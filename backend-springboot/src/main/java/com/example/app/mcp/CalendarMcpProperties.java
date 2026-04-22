package com.example.app.mcp;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "calendar.mcp")
public class CalendarMcpProperties {
  private boolean enabled = true;
  private boolean autostart = true;

  private String upstreamHost = "127.0.0.1";
  private int upstreamPort = 8001;

  // Optional overrides for auto-start
  private String pythonRootDir;
  private String pythonExecutable;

  public boolean isEnabled() {
    return enabled;
  }

  public void setEnabled(boolean enabled) {
    this.enabled = enabled;
  }

  public boolean isAutostart() {
    return autostart;
  }

  public void setAutostart(boolean autostart) {
    this.autostart = autostart;
  }

  public String getUpstreamHost() {
    return upstreamHost;
  }

  public void setUpstreamHost(String upstreamHost) {
    this.upstreamHost = upstreamHost;
  }

  public int getUpstreamPort() {
    return upstreamPort;
  }

  public void setUpstreamPort(int upstreamPort) {
    this.upstreamPort = upstreamPort;
  }

  public String getPythonRootDir() {
    return pythonRootDir;
  }

  public void setPythonRootDir(String pythonRootDir) {
    this.pythonRootDir = pythonRootDir;
  }

  public String getPythonExecutable() {
    return pythonExecutable;
  }

  public void setPythonExecutable(String pythonExecutable) {
    this.pythonExecutable = pythonExecutable;
  }

  public String upstreamBaseUrl() {
    return "http://" + upstreamHost + ":" + upstreamPort;
  }
}

