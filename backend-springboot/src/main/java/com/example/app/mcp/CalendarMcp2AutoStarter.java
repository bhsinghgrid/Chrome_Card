package com.example.app.mcp;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

@Component
public class CalendarMcp2AutoStarter implements ApplicationRunner {
  private static final Logger log = LoggerFactory.getLogger(CalendarMcp2AutoStarter.class);

  private final CalendarMcp2Properties properties;
  private final PythonMcpServer2 pythonMcpServer2;

  public CalendarMcp2AutoStarter(CalendarMcp2Properties properties, PythonMcpServer2 pythonMcpServer2) {
    this.properties = properties;
    this.pythonMcpServer2 = pythonMcpServer2;
  }

  @Override
  public void run(ApplicationArguments args) {
    if (!properties.isEnabled() || !properties.isAutostart()) {
      return;
    }
    pythonMcpServer2.ensureStarted();
    if (!pythonMcpServer2.isHealthy()) {
      log.warn("Python MCP2 server is not healthy; `/mcp2/**` proxy calls will return 502.");
    }
  }
}

