package com.example.app.mcp;

import jakarta.servlet.ServletOutputStream;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Arrays;
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
public class CalendarMcp2ProxyController {
  private static final Logger log = LoggerFactory.getLogger(CalendarMcp2ProxyController.class);
  private static final int SSE_PRELUDE_MAX_BYTES = 8 * 1024;

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

  private final CalendarMcp2Properties properties;
  private final PythonMcpServer2 pythonMcpServer2;
  private final HttpClient httpClient;

  public CalendarMcp2ProxyController(CalendarMcp2Properties properties, PythonMcpServer2 pythonMcpServer2) {
    this.properties = properties;
    this.pythonMcpServer2 = pythonMcpServer2;
    this.httpClient =
        HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1).connectTimeout(Duration.ofSeconds(5)).build();
  }

  @GetMapping(value = "/health/mcp2", produces = MediaType.APPLICATION_JSON_VALUE)
  public Map<String, Object> mcp2Health() {
    boolean healthy = pythonMcpServer2.isHealthy();
    return Map.of("status", healthy ? "ok" : "down", "upstream", properties.upstreamBaseUrl());
  }

  @RequestMapping({"/mcp2", "/mcp2/**", "/api/agent2", "/api/agent2/**"})
  public void proxy(HttpServletRequest request, HttpServletResponse response) throws IOException {
    if (!properties.isEnabled()) {
      response.setStatus(HttpServletResponse.SC_NOT_FOUND);
      return;
    }

    pythonMcpServer2.ensureStarted();
    if (properties.isAutostart() && !pythonMcpServer2.isHealthy()) {
      writeJsonError(
          response,
          HttpServletResponse.SC_BAD_GATEWAY,
          "MCP2 upstream is not running or not healthy at " + properties.upstreamBaseUrl());
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
      log.warn(
          "Proxy to MCP2 upstream failed for {} {} -> {}",
          request.getMethod(),
          request.getRequestURI(),
          targetUri,
          e);
      writeJsonError(response, HttpServletResponse.SC_BAD_GATEWAY, "Failed to reach MCP2 upstream.");
      return;
    }

    response.setStatus(upstreamResponse.statusCode());
    copyResponseHeaders(upstreamResponse, response);
    response.flushBuffer();

    try (InputStream in = upstreamResponse.body(); ServletOutputStream out = response.getOutputStream()) {
      if (shouldRewriteSseEndpointEvent(request, upstreamResponse)) {
        streamSseWithEndpointRewrite(in, out);
      } else {
        byte[] buffer = new byte[8192];
        int read;
        while ((read = in.read(buffer)) != -1) {
          out.write(buffer, 0, read);
          out.flush();
        }
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

    // Local endpoints are `/mcp2/**` and `/api/agent2/**`, but upstream uses `/mcp/**` and `/api/agent/**`.
    path = rewriteLocalPathToUpstream(path);

    String queryString = request.getQueryString();
    String baseUrl = properties.upstreamBaseUrl();
    String target = baseUrl + path + (queryString == null || queryString.isBlank() ? "" : "?" + queryString);
    return URI.create(target);
  }

  private String rewriteLocalPathToUpstream(String path) {
    if (path.equals("/mcp2") || path.startsWith("/mcp2/")) {
      return "/mcp" + path.substring("/mcp2".length());
    }
    if (path.equals("/api/agent2") || path.startsWith("/api/agent2/")) {
      return "/api/agent" + path.substring("/api/agent2".length());
    }
    return path;
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

  private boolean shouldRewriteSseEndpointEvent(
      HttpServletRequest request, HttpResponse<InputStream> upstreamResponse) {
    String localPath = extractRequestPath(request);
    if (!(localPath.equals("/mcp2/sse") || localPath.startsWith("/mcp2/sse/"))) {
      return false;
    }

    String contentType = upstreamResponse.headers().firstValue("content-type").orElse("");
    return contentType.toLowerCase(Locale.ROOT).contains("text/event-stream");
  }

  private void streamSseWithEndpointRewrite(InputStream in, ServletOutputStream out) throws IOException {
    // The first SSE event from upstream contains the message endpoint.
    // Rewrite it so clients keep talking to this Java server under `/mcp2/**`.
    ByteArrayOutputStream prelude = new ByteArrayOutputStream();
    byte[] buffer = new byte[1024];
    int read;
    int delimiterIndex = -1;
    int delimiterLength = 0;

    while ((read = in.read(buffer)) != -1) {
      prelude.write(buffer, 0, read);
      byte[] bytes = prelude.toByteArray();

      int idx = indexOf(bytes, "\n\n".getBytes(StandardCharsets.UTF_8));
      if (idx >= 0) {
        delimiterIndex = idx;
        delimiterLength = 2;
        break;
      }
      idx = indexOf(bytes, "\r\n\r\n".getBytes(StandardCharsets.UTF_8));
      if (idx >= 0) {
        delimiterIndex = idx;
        delimiterLength = 4;
        break;
      }

      if (prelude.size() >= SSE_PRELUDE_MAX_BYTES) {
        break;
      }
    }

    byte[] bytes = prelude.toByteArray();
    if (bytes.length > 0) {
      if (delimiterIndex >= 0) {
        int end = delimiterIndex + delimiterLength;
        byte[] firstEvent = Arrays.copyOfRange(bytes, 0, end);
        byte[] remainder = Arrays.copyOfRange(bytes, end, bytes.length);

        String firstEventText = new String(firstEvent, StandardCharsets.UTF_8);
        String rewrittenText = firstEventText.replace("/mcp/messages", "/mcp2/messages");
        out.write(rewrittenText.getBytes(StandardCharsets.UTF_8));
        if (remainder.length > 0) {
          out.write(remainder);
        }
      } else {
        String text = new String(bytes, StandardCharsets.UTF_8);
        String rewrittenText = text.replace("/mcp/messages", "/mcp2/messages");
        out.write(rewrittenText.getBytes(StandardCharsets.UTF_8));
      }
      out.flush();
    }

    // Stream the remainder as-is.
    while ((read = in.read(buffer)) != -1) {
      out.write(buffer, 0, read);
      out.flush();
    }
  }

  private String extractRequestPath(HttpServletRequest request) {
    String contextPath = request.getContextPath();
    String requestUri = request.getRequestURI();
    if (contextPath != null && !contextPath.isEmpty() && requestUri.startsWith(contextPath)) {
      return requestUri.substring(contextPath.length());
    }
    return requestUri;
  }

  private int indexOf(byte[] haystack, byte[] needle) {
    if (needle.length == 0 || haystack.length < needle.length) {
      return -1;
    }
    for (int i = 0; i <= haystack.length - needle.length; i++) {
      boolean matches = true;
      for (int j = 0; j < needle.length; j++) {
        if (haystack[i + j] != needle[j]) {
          matches = false;
          break;
        }
      }
      if (matches) {
        return i;
      }
    }
    return -1;
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
