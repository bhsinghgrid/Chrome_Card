package com.example.app.mcp;

import jakarta.annotation.PreDestroy;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
public class PythonMcpServer {
  private static final Logger log = LoggerFactory.getLogger(PythonMcpServer.class);

  private final CalendarMcpProperties properties;
  private final HttpClient httpClient;
  private final Object lifecycleLock = new Object();

  private Process process;

  public PythonMcpServer(CalendarMcpProperties properties) {
    this.properties = properties;
    this.httpClient =
        HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_1_1)
            .connectTimeout(Duration.ofSeconds(2))
            .followRedirects(HttpClient.Redirect.NORMAL)
            .build();
  }

  public void ensureStarted() {
    if (!properties.isEnabled() || !properties.isAutostart()) {
      return;
    }

    synchronized (lifecycleLock) {
      if (isHealthy()) {
        return;
      }

      if (process != null && process.isAlive()) {
        if (waitForHealthy(Duration.ofSeconds(15))) {
          return;
        }
        log.warn("Python MCP process is running but not healthy; restarting.");
        stopProcess();
      }

      try {
        startProcess();
      } catch (Exception e) {
        // Do not crash the Java backend on MCP startup issues; the proxy will return 502.
        log.error("Failed to start Python MCP server.", e);
      }
    }
  }

  public boolean isHealthy() {
    URI healthUri = URI.create(properties.upstreamBaseUrl() + "/health");
    HttpRequest request = HttpRequest.newBuilder(healthUri).timeout(Duration.ofSeconds(2)).GET().build();
    try {
      HttpResponse<Void> response = httpClient.send(request, HttpResponse.BodyHandlers.discarding());
      return response.statusCode() >= 200 && response.statusCode() < 300;
    } catch (IOException e) {
      return false;
    } catch (InterruptedException e) {
      Thread.currentThread().interrupt();
      return false;
    }
  }

  private boolean waitForHealthy(Duration timeout) {
    long deadlineNanos = System.nanoTime() + timeout.toNanos();
    while (System.nanoTime() < deadlineNanos) {
      if (isHealthy()) {
        return true;
      }
      try {
        Thread.sleep(500);
      } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
        return false;
      }
    }
    return false;
  }

  private void startProcess() throws IOException {
    Path rootDir = resolvePythonRootDir();
    String pythonExe = resolvePythonExecutable(rootDir);

    List<String> cmd = new ArrayList<>();
    cmd.add(pythonExe);
    cmd.add("-m");
    cmd.add("uvicorn");
    cmd.add("api_server:app");
    cmd.add("--host");
    cmd.add(properties.getUpstreamHost());
    cmd.add("--port");
    cmd.add(Integer.toString(properties.getUpstreamPort()));

    log.info("Starting Python MCP server (api_server.py) at {} (cwd: {}).", properties.upstreamBaseUrl(), rootDir);

    ProcessBuilder pb = new ProcessBuilder(cmd);
    pb.directory(rootDir.toFile());
    pb.inheritIO();
    pb.environment().putIfAbsent("PYTHONUNBUFFERED", "1");
    pb.environment().putIfAbsent("MCP_HOST", properties.getUpstreamHost());
    pb.environment().putIfAbsent("MCP_PORT", Integer.toString(properties.getUpstreamPort()));

    process = pb.start();

    if (!waitForHealthy(Duration.ofSeconds(20))) {
      stopProcess();
      throw new IOException("Python MCP server did not become healthy in time.");
    }

    log.info("Python MCP server is healthy at {}.", properties.upstreamBaseUrl());
  }

  private Path resolvePythonRootDir() throws IOException {
    String configuredRoot = properties.getPythonRootDir();
    if (configuredRoot != null && !configuredRoot.isBlank()) {
      Path root = Paths.get(configuredRoot).toAbsolutePath().normalize();
      if (!Files.exists(root.resolve("api_server.py"))) {
        throw new IOException("calendar.mcp.python-root-dir does not contain api_server.py: " + root);
      }
      return root;
    }

    Path cwd = Paths.get("").toAbsolutePath().normalize();
    Path current = cwd;
    while (current != null) {
      if (Files.exists(current.resolve("api_server.py"))) {
        return current;
      }
      current = current.getParent();
    }

    throw new IOException("Could not find api_server.py. Set calendar.mcp.python-root-dir.");
  }

  private String resolvePythonExecutable(Path rootDir) {
    String configuredExecutable = properties.getPythonExecutable();
    if (configuredExecutable != null && !configuredExecutable.isBlank()) {
      return configuredExecutable;
    }

    Path mcpVenvPython = rootDir.resolve(".venv-mcp").resolve("bin").resolve("python");
    if (Files.exists(mcpVenvPython)) {
      return mcpVenvPython.toAbsolutePath().toString();
    }

    Path venvPython = rootDir.resolve(".venv").resolve("bin").resolve("python");
    if (Files.exists(venvPython)) {
      return venvPython.toAbsolutePath().toString();
    }

    Path mcpVenvWindowsPython = rootDir.resolve(".venv-mcp").resolve("Scripts").resolve("python.exe");
    if (Files.exists(mcpVenvWindowsPython)) {
      return mcpVenvWindowsPython.toAbsolutePath().toString();
    }

    Path windowsPython = rootDir.resolve(".venv").resolve("Scripts").resolve("python.exe");
    if (Files.exists(windowsPython)) {
      return windowsPython.toAbsolutePath().toString();
    }

    return "python3";
  }

  @PreDestroy
  public void shutdown() {
    synchronized (lifecycleLock) {
      stopProcess();
    }
  }

  private void stopProcess() {
    if (process == null) {
      return;
    }
    if (!process.isAlive()) {
      process = null;
      return;
    }

    log.info("Stopping Python MCP server process.");
    process.destroy();
    try {
      if (!process.waitFor(5, TimeUnit.SECONDS)) {
        process.destroyForcibly();
      }
    } catch (InterruptedException e) {
      Thread.currentThread().interrupt();
      process.destroyForcibly();
    } finally {
      process = null;
    }
  }
}
