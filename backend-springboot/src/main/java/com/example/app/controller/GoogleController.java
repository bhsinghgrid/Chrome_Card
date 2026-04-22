package com.example.app.controller;

import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
@RequestMapping("/api")
public class GoogleController {

  @GetMapping("/calendar")
  public Map<String, Object> calendar(@RequestHeader("Authorization") String auth) {
    Map<String, Object> res = new HashMap<>();
    res.put("message", "Proxy endpoint for calendar");
    res.put("token", auth);
    return res;
  }

  @GetMapping("/gmail")
  public Map<String, Object> gmail(@RequestHeader("Authorization") String auth) {
    Map<String, Object> res = new HashMap<>();
    res.put("message", "Proxy endpoint for gmail");
    res.put("token", auth);
    return res;
  }
}