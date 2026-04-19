// Wait for DOM to be ready
function initializeExtension() {
  console.log("Google Dashboard Extension initializing...");
  
  let sidebarOpen = false;

  // Add global styles for animations
  const globalStyle = document.createElement("style");
  globalStyle.innerHTML = `
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    @keyframes slideIn {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
      from { transform: translateX(0); opacity: 1; }
      to { transform: translateX(100%); opacity: 0; }
    }
    
    /* Responsive adjustments for sidebar */
    body, html {
      transition: margin-right 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
      overflow-wrap: break-word;
      word-wrap: break-word;
    }
    
    html {
      width: 100%;
      height: 100%;
    }
    
    body {
      width: 100%;
    }
    
    @media (max-width: 480px) {
      #google-dashboard-button {
        width: 45px !important;
        height: 45px !important;
        right: 10px !important;
        bottom: 10px !important;
        font-size: 20px !important;
      }
      
      body, html {
        transition: margin-right 0.3s ease !important;
      }
    }
  `;
  if (document.head) {
    document.head.appendChild(globalStyle);
  }

  // Create toggle button with premium styling
  const button = document.createElement("button");
  button.id = "google-dashboard-button";
  button.innerText = "☰";
  button.style.position = "fixed";
  button.style.right = "20px";
  button.style.bottom = "20px";
  button.style.zIndex = "2147483647"; // Maximum z-index
  button.style.width = "50px";
  button.style.height = "50px";
  button.style.fontSize = "24px";
  button.style.cursor = "pointer";
  button.style.backgroundColor = "#4285F4";
  button.style.color = "white";
  button.style.border = "none";
  button.style.borderRadius = "50%";
  button.style.boxShadow = "0 4px 12px rgba(66, 133, 244, 0.4)";
  button.style.transition = "all 0.3s ease";
  button.style.fontWeight = "bold";
  button.style.display = "flex";
  button.style.alignItems = "center";
  button.style.justifyContent = "center";
  button.style.padding = "0";
  button.style.margin = "0";
  button.style.pointerEvents = "auto";
  button.style.visibility = "visible";
  button.style.opacity = "1";
  button.setAttribute("data-extension", "google-dashboard");

  button.onmouseover = () => {
    button.style.backgroundColor = "#3367D6";
    button.style.boxShadow = "0 6px 16px rgba(66, 133, 244, 0.6)";
    button.style.transform = "scale(1.1)";
  };

  button.onmouseout = () => {
    button.style.backgroundColor = "#4285F4";
    button.style.boxShadow = "0 4px 12px rgba(66, 133, 244, 0.4)";
    button.style.transform = "scale(1)";
  };

  // Add button to page - retry if body isn't ready
  const addButtonToDom = () => {
    if (document.body) {
      try {
        document.body.appendChild(button);
        console.log("✅ Button successfully added to page");
      } catch (err) {
        console.error("Error appending button:", err);
      }
    } else {
      // Retry if body doesn't exist yet
      setTimeout(addButtonToDom, 100);
    }
  };
  
  addButtonToDom();

  button.onclick = () => {
    if (sidebarOpen) {
      const sidebar = document.getElementById("google-sidebar");
      const overlay = document.getElementById("google-overlay");
      if (sidebar) {
        sidebar.style.animation = "slideOut 0.3s ease";
        setTimeout(() => {
          sidebar.remove();
          if (overlay) overlay.remove();
          
          // Restore all styles
          document.body.style.overflow = "";
          document.body.style.marginRight = "0";
          document.documentElement.style.marginRight = "0";
          document.documentElement.style.overflow = "";
          document.documentElement.style.width = "100%";
          
          // Remove transitions
          document.body.style.transition = "";
          document.documentElement.style.transition = "";
          
          // Restore button position
          const screenWidth = window.innerWidth;
          if (screenWidth >= 768) {
            button.style.right = "20px";
          }
        }, 400);
      }
      sidebarOpen = false;
    } else {
      // Create overlay for better UX
      const overlay = document.createElement("div");
      overlay.id = "google-overlay";
      overlay.style.position = "fixed";
      overlay.style.top = "0";
      overlay.style.left = "0";
      overlay.style.right = "0";
      overlay.style.bottom = "0";
      overlay.style.backgroundColor = "rgba(0, 0, 0, 0.2)";
      overlay.style.zIndex = "999997";
      overlay.style.animation = "fadeIn 0.3s ease";
      overlay.style.backdropFilter = "blur(2px)";
      overlay.onclick = () => button.onclick(); // Close on overlay click
      document.body.appendChild(overlay);
      
      createSidebar();
      sidebarOpen = true;
    }
  };

  function createSidebar() {
    const sidebar = document.createElement("div");
    sidebar.id = "google-sidebar";
    sidebar.style.position = "fixed";
    sidebar.style.top = "0";
    sidebar.style.right = "0";
    sidebar.style.height = "100vh";
    sidebar.style.background = "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)";
    sidebar.style.color = "#fff";
    sidebar.style.zIndex = "999998";
    sidebar.style.overflow = "auto";
    sidebar.style.boxShadow = "-4px 0 30px rgba(0,0,0,0.5)";
    sidebar.style.fontFamily = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
    sidebar.style.animation = "slideIn 0.3s ease";
    
    // Responsive width and push content
    const screenWidth = window.innerWidth;
    let sidebarWidth = "420px";
    
    if (screenWidth < 480) {
      sidebarWidth = "100%"; // Full width on very small mobile
      sidebar.style.width = sidebarWidth;
      // Push full width on mobile to show content moved
      document.body.style.marginRight = sidebarWidth;
      document.documentElement.style.marginRight = sidebarWidth;
    } else if (screenWidth < 768) {
      sidebarWidth = "85%"; // 85% width on mobile
      sidebar.style.width = sidebarWidth;
      // Push content to left
      document.body.style.marginRight = sidebarWidth;
      document.documentElement.style.marginRight = sidebarWidth;
    } else if (screenWidth < 1024) {
      sidebarWidth = "350px"; // Medium width on tablet
      sidebar.style.width = sidebarWidth;
      // Push content to left
      document.body.style.marginRight = sidebarWidth;
      document.documentElement.style.marginRight = sidebarWidth;
    } else {
      sidebarWidth = "420px"; // Standard width on desktop
      sidebar.style.width = sidebarWidth;
      // Push content to left
      document.body.style.marginRight = sidebarWidth;
      document.documentElement.style.marginRight = sidebarWidth;
    }
    
    // Store sidebar width for later use
    sidebar.setAttribute("data-width", sidebarWidth);
    
    // Smooth transition for content shift
    document.body.style.transition = "margin-right 0.4s cubic-bezier(0.4, 0, 0.2, 1)";
    document.documentElement.style.transition = "margin-right 0.4s cubic-bezier(0.4, 0, 0.2, 1)";
    document.documentElement.style.overflow = "hidden";
    
    // Add smooth animation for all main content
    const allElements = document.querySelectorAll("body > *:not(#google-sidebar):not(#google-overlay)");
    allElements.forEach(el => {
      if (el.style.position !== "fixed") {
        el.style.transition = "margin-right 0.4s cubic-bezier(0.4, 0, 0.2, 1)";
      }
    });
    
    sidebar.innerHTML = `
      <style>
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
          from { transform: translateX(0); opacity: 1; }
          to { transform: translateX(100%); opacity: 0; }
        }
        
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        #google-sidebar h3 {
          background: linear-gradient(135deg, #4285F4 0%, #34A853 100%);
          margin: 0;
          padding: 20px;
          font-size: 20px;
          font-weight: 700;
          text-align: center;
          border-bottom: 2px solid rgba(255,255,255,0.1);
          box-shadow: 0 4px 12px rgba(66, 133, 244, 0.2);
        }
        
        /* Tab Navigation */
        #google-sidebar .tab-nav {
          display: flex;
          gap: 0;
          padding: 0;
          margin: 0;
          background: rgba(0,0,0,0.3);
          border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        
        #google-sidebar .tab-btn {
          flex: 1;
          padding: 12px 8px;
          background: transparent;
          border: none;
          color: rgba(255,255,255,0.6);
          cursor: pointer;
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          transition: all 0.3s ease;
          border-bottom: 3px solid transparent;
          position: relative;
        }
        
        #google-sidebar .tab-btn:hover {
          color: rgba(255,255,255,0.9);
          background: rgba(255,255,255,0.05);
        }
        
        #google-sidebar .tab-btn.active {
          color: #60a5fa;
          border-bottom-color: #60a5fa;
          background: rgba(96, 165, 250, 0.1);
        }
        
        /* Tab Content */
        #google-sidebar .tab-content {
          display: none;
          animation: fadeIn 0.3s ease;
        }
        
        #google-sidebar .tab-content.active {
          display: block;
        }
        
        #google-sidebar .section-container {
          padding: 0;
        }
        
        #google-sidebar .section {
          padding: 20px;
          border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        
        #google-sidebar .section:last-child {
          border-bottom: none;
        }
        
        #google-sidebar .section-title {
          font-size: 18px;
          font-weight: 700;
          margin: 0 0 15px 0;
          display: flex;
          align-items: center;
          gap: 10px;
          color: #60a5fa;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          font-size: 14px;
        }
        
        /* Settings Styles */
        #google-sidebar .settings-group {
          margin-bottom: 20px;
          padding-bottom: 15px;
          border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        
        #google-sidebar .settings-group:last-child {
          border-bottom: none;
          margin-bottom: 0;
          padding-bottom: 0;
        }
        
        #google-sidebar .settings-label {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 13px;
          color: #e2e8f0;
          margin-bottom: 8px;
          font-weight: 500;
        }
        
        #google-sidebar .switch {
          position: relative;
          display: inline-block;
          width: 40px;
          height: 24px;
        }
        
        #google-sidebar .switch input {
          opacity: 0;
          width: 0;
          height: 0;
        }
        
        #google-sidebar .slider {
          position: absolute;
          cursor: pointer;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: rgba(255,255,255,0.1);
          transition: 0.3s;
          border-radius: 24px;
          border: 1px solid rgba(255,255,255,0.15);
        }
        
        #google-sidebar .slider:before {
          position: absolute;
          content: "";
          height: 18px;
          width: 18px;
          left: 3px;
          bottom: 2px;
          background-color: white;
          transition: 0.3s;
          border-radius: 50%;
        }
        
        #google-sidebar input:checked + .slider {
          background-color: #60a5fa;
          border-color: #60a5fa;
        }
        
        #google-sidebar input:checked + .slider:before {
          transform: translateX(16px);
        }
        
        #google-sidebar .btn-group {
          display: flex;
          gap: 8px;
          margin-top: 15px;
          flex-wrap: wrap;
        }
        
        #google-sidebar .settings-btn {
          flex: 1;
          padding: 10px 12px;
          background: linear-gradient(135deg, rgba(96, 165, 250, 0.3) 0%, rgba(59, 130, 246, 0.2) 100%);
          border: 1px solid rgba(96, 165, 250, 0.3);
          color: #60a5fa;
          border-radius: 6px;
          cursor: pointer;
          font-size: 12px;
          font-weight: 600;
          transition: all 0.3s ease;
        }
        
        #google-sidebar .settings-btn:hover {
          background: linear-gradient(135deg, rgba(96, 165, 250, 0.5) 0%, rgba(59, 130, 246, 0.4) 100%);
          border-color: rgba(96, 165, 250, 0.5);
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(96, 165, 250, 0.2);
        }
        
        #google-sidebar .event-card {
          background: linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.04) 100%);
          border-left: 4px solid #4285F4;
          padding: 14px;
          margin-bottom: 12px;
          border-radius: 8px;
          font-size: 13px;
          line-height: 1.6;
          transition: all 0.3s ease;
          backdrop-filter: blur(10px);
          cursor: pointer;
          word-wrap: break-word;
        }
        
        #google-sidebar .event-card:hover {
          background: linear-gradient(135deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.08) 100%);
          border-left-color: #34A853;
          transform: translateX(5px);
          box-shadow: 0 4px 12px rgba(52, 168, 83, 0.2);
        }
        
        #google-sidebar .event-card.calendar {
          border-left-color: #EA4335;
        }
        
        #google-sidebar .event-card.calendar:hover {
          border-left-color: #EA4335;
          box-shadow: 0 4px 12px rgba(234, 67, 53, 0.2);
        }
        
        #google-sidebar .event-card.email {
          border-left-color: #FBBC04;
        }
        
        #google-sidebar .event-card.email:hover {
          border-left-color: #FBBC04;
          box-shadow: 0 4px 12px rgba(251, 188, 4, 0.2);
        }
        
        #google-sidebar .event-title {
          font-weight: 600;
          color: #fff;
          margin-bottom: 6px;
          display: block;
          word-wrap: break-word;
        }
        
        #google-sidebar .event-meta {
          font-size: 12px;
          opacity: 0.8;
          color: #cbd5e1;
          word-wrap: break-word;
        }
        
        #google-sidebar .event-time {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-top: 6px;
          color: #60a5fa;
          flex-wrap: wrap;
        }
        
        #google-sidebar .empty-state {
          text-align: center;
          padding: 30px 15px;
          font-size: 13px;
          opacity: 0.6;
          background: rgba(255,255,255,0.03);
          border-radius: 8px;
          border: 1px dashed rgba(255,255,255,0.1);
        }
        
        #google-sidebar .loading {
          text-align: center;
          padding: 20px;
          font-size: 13px;
          opacity: 0.8;
          animation: fadeIn 0.5s ease;
        }
        
        #google-sidebar::-webkit-scrollbar {
          width: 8px;
        }
        
        #google-sidebar::-webkit-scrollbar-track {
          background: transparent;
        }
        
        #google-sidebar::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.15);
          border-radius: 4px;
        }
        
        #google-sidebar::-webkit-scrollbar-thumb:hover {
          background: rgba(255,255,255,0.25);
        }
        
        #google-sidebar .badge {
          display: inline-block;
          background: rgba(66, 133, 244, 0.3);
          color: #60a5fa;
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 11px;
          margin-top: 6px;
          font-weight: 600;
        }
        
        /* Mobile responsiveness */
        @media (max-width: 768px) {
          #google-sidebar {
            border-radius: 0 !important;
          }
          
          #google-sidebar h3 {
            padding: 16px;
            font-size: 18px;
          }
          
          #google-sidebar .tab-nav {
            flex-wrap: wrap;
          }
          
          #google-sidebar .tab-btn {
            padding: 10px 6px;
            font-size: 10px;
            flex: 1;
            min-width: 80px;
          }
          
          #google-sidebar .section {
            padding: 12px;
          }
          
          #google-sidebar .section-title {
            font-size: 11px;
            gap: 5px;
          }
          
          #google-sidebar .event-card {
            padding: 10px;
            font-size: 11px;
            margin-bottom: 8px;
          }
          
          #google-sidebar .event-title {
            font-size: 13px;
          }
          
          #google-sidebar .event-meta {
            font-size: 10px;
          }
          
          #google-sidebar .settings-label {
            font-size: 12px;
          }
          
          #google-sidebar .settings-btn {
            padding: 8px 10px;
            font-size: 11px;
          }
        }
        
        @media (max-width: 480px) {
          #google-sidebar {
            width: 100% !important;
            border-radius: 0 !important;
          }
          
          #google-sidebar h3 {
            padding: 14px;
            font-size: 16px;
            margin: 0;
          }
          
          #google-sidebar .tab-nav {
            flex-direction: row;
          }
          
          #google-sidebar .tab-btn {
            padding: 8px 4px;
            font-size: 9px;
            flex: 1;
            border-bottom-width: 2px;
          }
          
          #google-sidebar .section {
            padding: 10px;
          }
          
          #google-sidebar .section-title {
            font-size: 10px;
          }
          
          #google-sidebar .event-card {
            padding: 8px;
            font-size: 10px;
            border-left-width: 3px;
          }
          
          #google-sidebar .event-title {
            font-size: 12px;
            margin-bottom: 4px;
          }
          
          #google-sidebar .loading {
            padding: 15px;
          }
          
          #google-sidebar .empty-state {
            padding: 20px 10px;
          }
          
          #google-sidebar .settings-label {
            font-size: 11px;
          }
          
          #google-sidebar .settings-group {
            margin-bottom: 12px;
            padding-bottom: 12px;
          }
          
          #google-sidebar .settings-btn {
            padding: 8px 6px;
            font-size: 10px;
          }
          
          #google-sidebar .switch {
            width: 36px;
            height: 20px;
          }
          
          #google-sidebar .slider:before {
            height: 16px;
            width: 16px;
          }
          
          #google-sidebar input:checked + .slider:before {
            transform: translateX(14px);
          }
        }
      </style>
      
      <h3>📊 Google Dashboard</h3>
      
      <!-- Tab Navigation -->
      <div class="tab-nav">
        <button class="tab-btn active" onclick="switchTab('dashboard')">📅 Dashboard</button>
        <button class="tab-btn" onclick="switchTab('settings')">⚙️ Settings</button>
      </div>
      
      <!-- Dashboard Tab -->
      <div id="dashboard-tab" class="tab-content active">
        <div class="section-container">
          <div class="section">
            <div class="section-title">📅 Upcoming Events</div>
            <div id="calendar" class="loading">Loading calendar...</div>
          </div>
          
          <div class="section">
            <div class="section-title">📧 New Messages</div>
            <div id="gmail" class="loading">Loading emails...</div>
          </div>
        </div>
      </div>
      
      <!-- Settings Tab -->
      <div id="settings-tab" class="tab-content">
        <div class="section-container" style="padding: 20px;">
          <div style="margin-bottom: 8px; color: #60a5fa; font-weight: 600; font-size: 13px;">NOTIFICATIONS</div>
          
          <div class="settings-group">
            <div class="settings-label">
              <span>Enable Calendar Alerts</span>
              <label class="switch">
                <input type="checkbox" id="cal-alerts" checked>
                <span class="slider"></span>
              </label>
            </div>
          </div>
          
          <div class="settings-group">
            <div class="settings-label">
              <span>Enable Email Notifications</span>
              <label class="switch">
                <input type="checkbox" id="email-alerts" checked>
                <span class="slider"></span>
              </label>
            </div>
          </div>
          
          <div class="settings-group">
            <div class="settings-label">
              <span>Auto-Refresh (seconds)</span>
              <input type="number" id="refresh-interval" value="30" style="width: 60px; padding: 4px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); color: white; border-radius: 4px; font-size: 12px;">
            </div>
          </div>
          
          <div style="margin-bottom: 8px; margin-top: 20px; color: #60a5fa; font-weight: 600; font-size: 13px;">ACCOUNT</div>
          
          <div class="settings-group">
            <div class="settings-label">
              <span>Sync Status</span>
              <span style="color: #34A853; font-size: 11px; font-weight: 600;">✓ Connected</span>
            </div>
          </div>
          
          <div class="settings-group">
            <div class="settings-label">
              <span>Last Updated</span>
              <span id="last-updated" style="color: #cbd5e1; font-size: 11px;">Just now</span>
            </div>
          </div>
          
          <div class="btn-group">
            <button class="settings-btn" onclick="refreshData()">🔄 Refresh Now</button>
            <button class="settings-btn" onclick="clearCache()">🗑️ Clear Cache</button>
          </div>
          
          <div class="btn-group">
            <button class="settings-btn" style="flex: 1;" onclick="logout()">🚪 Logout</button>
          </div>
          
          <div style="margin-top: 25px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.08); color: #64748b; font-size: 11px; line-height: 1.5;">
            <div><strong>Google Dashboard Extension</strong></div>
            <div>Version 1.0</div>
            <div style="margin-top: 8px;">Connect your Google Calendar and Gmail in one sidebar.</div>
          </div>
        </div>
      </div>
      
      <script>
        window.switchTab = function(tab) {
          // Hide all tabs
          document.getElementById('dashboard-tab').classList.remove('active');
          document.getElementById('settings-tab').classList.remove('active');
          
          // Remove active class from buttons
          document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
          
          // Show selected tab
          if (tab === 'dashboard') {
            document.getElementById('dashboard-tab').classList.add('active');
            document.querySelectorAll('.tab-btn')[0].classList.add('active');
          } else if (tab === 'settings') {
            document.getElementById('settings-tab').classList.add('active');
            document.querySelectorAll('.tab-btn')[1].classList.add('active');
          }
        };
        
        window.refreshData = function() {
          const btn = event.target;
          btn.disabled = true;
          btn.textContent = '⏳ Refreshing...';
          setTimeout(() => {
            btn.disabled = false;
            btn.textContent = '🔄 Refresh Now';
            loadData();
            document.getElementById('last-updated').textContent = 'Just now';
          }, 800);
        };
        
        window.clearCache = function() {
          chrome.storage.local.clear(() => {
            alert('Cache cleared!');
            loadData();
          });
        };
        
        window.logout = function() {
          chrome.identity.clearAllCachedAuthTokens(() => {
            chrome.storage.local.clear(() => {
              window.location.reload();
            });
          });
        };
      </script>
    `;
    
    document.body.appendChild(sidebar);
    
    // Add scroll protection to prevent body scroll when sidebar is open
    document.body.style.overflow = "hidden";
    
    // Close sidebar on ESC key
    const handleEsc = (e) => {
      if (e.key === "Escape") {
        button.onclick();
        document.removeEventListener("keydown", handleEsc);
      }
    };
    document.addEventListener("keydown", handleEsc);
    
    loadData();
  }

  function formatDateTime(dateTime) {
    try {
      const date = new Date(dateTime);
      const today = new Date();
      const tomorrow = new Date(today);
      tomorrow.setDate(tomorrow.getDate() + 1);
      
      const isToday = date.toDateString() === today.toDateString();
      const isTomorrow = date.toDateString() === tomorrow.toDateString();
      
      if (isToday) {
        return `Today at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
      } else if (isTomorrow) {
        return `Tomorrow at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
      } else {
        return date.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
      }
    } catch (e) {
      return dateTime;
    }
  }

  function isFutureEvent(item) {
    try {
      const eventDate = new Date(item.start.dateTime || item.start.date);
      return eventDate > new Date();
    } catch (e) {
      return true;
    }
  }

  function loadData() {
    chrome.runtime.sendMessage({ type: "GET_DATA" }, (response) => {
      const calendarDiv = document.getElementById("calendar");
      const gmailDiv = document.getElementById("gmail");
      
      if (!calendarDiv || !gmailDiv) return;
      
      console.log("Response received:", response);
      
      if (!response) {
        calendarDiv.innerHTML = '<div class="empty-state">⚠️ No response from extension</div>';
        gmailDiv.innerHTML = '<div class="empty-state">⚠️ Please login first</div>';
        return;
      }
      
      if (response.error) {
        console.error("Error response:", response.error);
        calendarDiv.innerHTML = '<div class="empty-state">⚠️ Error: ' + response.error + '</div>';
        gmailDiv.innerHTML = '<div class="empty-state">⚠️ Error: ' + response.error + '</div>';
        return;
      }

      // Display Calendar - Filter for future events only
      if (response.calendar && response.calendar.items && response.calendar.items.length > 0) {
        const futureEvents = response.calendar.items.filter(isFutureEvent);
        console.log("Future events:", futureEvents);
        
        if (futureEvents.length > 0) {
          calendarDiv.innerHTML = futureEvents
            .slice(0, 8)
            .map(item => {
              const startDate = item.start.dateTime || item.start.date;
              const eventName = item.summary || 'Untitled Event';
              const formattedTime = formatDateTime(startDate);
              
              return `
                <div class="event-card calendar">
                  <span class="event-title">${eventName}</span>
                  <div class="event-time">🕐 ${formattedTime}</div>
                  ${item.location ? `<div class="event-meta">📍 ${item.location}</div>` : ''}
                </div>
              `;
            })
            .join("");
        } else {
          calendarDiv.innerHTML = '<div class="empty-state">✨ No upcoming events scheduled</div>';
        }
      } else {
        console.log("No calendar data available");
        calendarDiv.innerHTML = '<div class="empty-state">✨ No events found</div>';
      }

      // Display Gmail - Enhanced with better formatting
      if (response.gmail && response.gmail.messages && response.gmail.messages.length > 0) {
        console.log("Gmail messages:", response.gmail.messages);
        gmailDiv.innerHTML = response.gmail.messages
          .slice(0, 8)
          .map((msg, idx) => {
            const subject = msg.subject || '(No Subject)';
            const from = msg.from || 'Unknown Sender';
            const fromName = from.match(/([^<]+)/)?.[1]?.trim() || from;
            const date = msg.date || '';
            
            let dateFormatted = '';
            try {
              dateFormatted = new Date(date).toLocaleDateString();
            } catch (e) {
              dateFormatted = date;
            }
            
            return `
              <div class="event-card email">
                <span class="event-title">${subject}</span>
                <div class="event-meta">From: ${fromName}</div>
                ${dateFormatted ? `<div class="event-meta">📬 ${dateFormatted}</div>` : ''}
                <span class="badge">New</span>
              </div>
            `;
          })
          .join("");
      } else {
        console.log("No gmail data available");
        gmailDiv.innerHTML = '<div class="empty-state">✨ All caught up!</div>';
      }
    });
  }
}

// Initialize when document is ready
console.log("Google Dashboard content script loaded! readyState:", document.readyState);

if (document.readyState === 'loading') {
  // DOM still loading
  document.addEventListener('DOMContentLoaded', () => {
    console.log("DOMContentLoaded event fired");
    initializeExtension();
  });
} else if (document.readyState === 'interactive') {
  // DOM ready but resources still loading
  console.log("Document interactive, initializing now");
  initializeExtension();
} else {
  // Everything loaded
  console.log("Document complete, initializing now");
  initializeExtension();
}

// Also initialize on document start as a fallback
if (document.documentElement) {
  setTimeout(() => {
    if (!document.getElementById("google-dashboard-button")) {
      console.log("Button not found, re-initializing...");
      initializeExtension();
    }
  }, 500);
}