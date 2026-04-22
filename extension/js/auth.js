function setStatus(text, ok) {
  const el = document.getElementById("status");
  if (!el) return;
  el.textContent = text;
  el.style.background = ok === true ? "#ecfdf5" : ok === false ? "#fef2f2" : "#f3f4f6";
  el.style.color = ok === true ? "#065f46" : ok === false ? "#991b1b" : "#111827";
}

function refreshStatus() {
  setStatus("Status: Checking...", null);
  chrome.runtime.sendMessage({ type: "CHECK_AUTH" }, (res) => {
    if (chrome.runtime.lastError) {
      setStatus(`Status: Error (${chrome.runtime.lastError.message})`, false);
      return;
    }
    if (!res || !res.success) {
      setStatus(`Status: Error (${(res && res.error) || "no response"})`, false);
      return;
    }
    if (res.connected) {
      setStatus("Status: Connected", true);
    } else {
      setStatus("Status: Not connected", false);
    }
  });
}

async function login() {
  setStatus("Status: Logging in...", null);
  chrome.runtime.sendMessage({ type: "LOGIN" }, (res) => {
    if (chrome.runtime.lastError) {
      console.error("Login error:", chrome.runtime.lastError.message);
      setStatus(`Status: Error (${chrome.runtime.lastError.message})`, false);
      return;
    }
    if (!res || !res.success) {
      console.error("Login failed:", (res && res.error) || "unknown error");
      setStatus(`Status: Error (${(res && res.error) || "login failed"})`, false);
      return;
    }
    console.log("Logged in");
    refreshStatus();
  });
}

async function logout() {
  setStatus("Status: Logging out...", null);
  chrome.runtime.sendMessage({ type: "LOGOUT" }, (res) => {
    if (chrome.runtime.lastError) {
      console.error("Logout error:", chrome.runtime.lastError.message);
      setStatus(`Status: Error (${chrome.runtime.lastError.message})`, false);
      return;
    }
    if (!res || !res.success) {
      console.error("Logout failed:", (res && res.error) || "unknown error");
      setStatus(`Status: Error (${(res && res.error) || "logout failed"})`, false);
      return;
    }
    console.log("Logged out");
    refreshStatus();
  });
}

document.getElementById("login").addEventListener("click", login);
document.getElementById("logout").addEventListener("click", logout);

refreshStatus();
