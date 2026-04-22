package com.example.app.mcp;

import jakarta.servlet.ServletOutputStream;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Enumeration;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class CalendarMcpProxyController {
  private static final Logger log = LoggerFactory.getLogger(CalendarMcpProxyController.class);

  private static final Set<String> HOP_BY_HOP_HEADERS =
      Set.of(
          "connection",
          "keep-alive",
          "proxy-authenticate",
          "proxy-authorization",
          "te",
          "trailer",
          "transfer-encoding",
          "upgrade",
          "host",
          "content-length");

  private final CalendarMcpProperties properties;
  private final PythonMcpServer pythonMcpServer;
  private final HttpClient httpClient;

  public CalendarMcpProxyController(CalendarMcpProperties properties, PythonMcpServer pythonMcpServer) {
    this.properties = properties;
    this.pythonMcpServer = pythonMcpServer;
    this.httpClient =
        HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1).connectTimeout(Duration.ofSeconds(5)).build();
  }

  @GetMapping(value = "/health/mcp", produces = MediaType.APPLICATION_JSON_VALUE)
  public Map<String, Object> mcpHealth() {
    boolean healthy = pythonMcpServer.isHealthy();
    return Map.of("status", healthy ? "ok" : "down", "upstream", properties.upstreamBaseUrl());
  }

  @RequestMapping({"/mcp", "/mcp/**", "/api/agent", "/api/agent/**"})
  public void proxy(HttpServletRequest request, HttpServletResponse response) throws IOException {
    if (!properties.isEnabled()) {
      response.setStatus(HttpServletResponse.SC_NOT_FOUND);
      return;
    }

    pythonMcpServer.ensureStarted();
    if (properties.isAutostart() && !pythonMcpServer.isHealthy()) {
      writeJsonError(
          response,
          HttpServletResponse.SC_BAD_GATEWAY,
          "Python MCP bridge is not running or not healthy at " + properties.upstreamBaseUrl());
      return;
    }

    URI targetUri = buildTargetUri(request);
    HttpRequest upstreamRequest;
    try {
      upstreamRequest = buildUpstreamRequest(request, targetUri);
    } catch (IOException e) {
      writeJsonError(response, HttpServletResponse.SC_BAD_GATEWAY, "Failed to read request body.");
      return;
    }

    HttpResponse<InputStream> upstreamResponse;
    try {
      upstreamResponse = httpClient.send(upstreamRequest, HttpResponse.BodyHandlers.ofInputStream());
    } catch (InterruptedException e) {
      Thread.currentThread().interrupt();
      writeJsonError(response, HttpServletResponse.SC_BAD_GATEWAY, "Proxy interrupted.");
      return;
    } catch (IOException e) {
      log.warn("Proxy to Python MCP failed for {} {} -> {}", request.getMethod(), request.getRequestURI(), targetUri, e);
      writeJsonError(response, HttpServletResponse.SC_BAD_GATEWAY, "Failed to reach Python MCP bridge.");
      return;
    }

    response.setStatus(upstreamResponse.statusCode());
    copyResponseHeaders(upstreamResponse, response);
    response.flushBuffer();

    try (InputStream in = upstreamResponse.body(); ServletOutputStream out = response.getOutputStream()) {
      byte[] buffer = new byte[8192];
      int read;
      while ((read = in.read(buffer)) != -1) {
        out.write(buffer, 0, read);
        out.flush();
      }
    }
  }

  private URI buildTargetUri(HttpServletRequest request) {
    String contextPath = request.getContextPath();
    String requestUri = request.getRequestURI();
    String path = requestUri;
    if (contextPath != null && !contextPath.isEmpty() && requestUri.startsWith(contextPath)) {
      path = requestUri.substring(contextPath.length());
    }
    String queryString = request.getQueryString();
    String baseUrl = properties.upstreamBaseUrl();
    String target = baseUrl + path + (queryString == null || queryString.isBlank() ? "" : "?" + queryString);
    return URI.create(target);
  }

  private HttpRequest buildUpstreamRequest(HttpServletRequest request, URI targetUri) throws IOException {
    String method = request.getMethod();
    boolean methodAllowsBody =
        !method.equalsIgnoreCase("GET") && !method.equalsIgnoreCase("HEAD") && !method.equalsIgnoreCase("OPTIONS");

    byte[] bodyBytes = methodAllowsBody ? request.getInputStream().readAllBytes() : new byte[0];

    HttpRequest.BodyPublisher bodyPublisher =
        bodyBytes.length > 0 ? HttpRequest.BodyPublishers.ofByteArray(bodyBytes) : HttpRequest.BodyPublishers.noBody();

    HttpRequest.Builder builder = HttpRequest.newBuilder(targetUri).method(method, bodyPublisher);

    Enumeration<String> headerNames = request.getHeaderNames();
    while (headerNames != null && headerNames.hasMoreElements()) {
      String headerName = headerNames.nextElement();
      if (shouldSkipHeader(headerName)) {
        continue;
      }
      Enumeration<String> values = request.getHeaders(headerName);
      while (values != null && values.hasMoreElements()) {
        builder.header(headerName, values.nextElement());
      }
    }

    return builder.build();
  }

  private void copyResponseHeaders(HttpResponse<?> upstreamResponse, HttpServletResponse response) {
    upstreamResponse
        .headers()
        .map()
        .forEach(
            (name, values) -> {
              if (name == null || shouldSkipHeader(name)) {
                return;
              }
              for (String value : values) {
                response.addHeader(name, value);
              }
            });
  }

  private boolean shouldSkipHeader(String headerName) {
    if (headerName == null) {
      return true;
    }
    return HOP_BY_HOP_HEADERS.contains(headerName.toLowerCase(Locale.ROOT));
  }

  private void writeJsonError(HttpServletResponse response, int statusCode, String message) throws IOException {
    response.setStatus(statusCode);
    response.setContentType(MediaType.APPLICATION_JSON_VALUE);
    response.getWriter().write("{\"error\":\"" + escapeJson(message) + "\"}");
  }

  private String escapeJson(String s) {
    // Minimal escaping for error messages.
    return s.replace("\\", "\\\\").replace("\"", "\\\"");
  }
}
