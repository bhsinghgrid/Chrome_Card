package com.example.app.mcp;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

@Component
public class CalendarMcpAutoStarter implements ApplicationRunner {
  private static final Logger log = LoggerFactory.getLogger(CalendarMcpAutoStarter.class);

  private final CalendarMcpProperties properties;
  private final PythonMcpServer pythonMcpServer;

  public CalendarMcpAutoStarter(CalendarMcpProperties properties, PythonMcpServer pythonMcpServer) {
    this.properties = properties;
    this.pythonMcpServer = pythonMcpServer;
  }

  @Override
  public void run(ApplicationArguments args) {
    if (!properties.isEnabled() || !properties.isAutostart()) {
      return;
    }
    pythonMcpServer.ensureStarted();
    if (!pythonMcpServer.isHealthy()) {
      log.warn("Python MCP server is not healthy; `/mcp/**` and `/api/agent/**` proxy calls will return 502.");
    }
  }
}

