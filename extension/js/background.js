// background.js

// Get token from Chrome Identity (BEST method)
async function getToken() {
  return new Promise((resolve, reject) => {
    chrome.identity.getAuthToken({ interactive: true }, (token) => {
      if (chrome.runtime.lastError) {
        console.error("Auth Error:", chrome.runtime.lastError);
        reject(chrome.runtime.lastError);
      } else if (token) {
        resolve(token);
      } else {
        reject("No token received");
      }
    });
  });
}

// Fetch Calendar
async function fetchCalendar() {
  try {
    const token = await getToken();
    console.log("Token received for Calendar");

    const res = await fetch(
      "https://www.googleapis.com/calendar/v3/calendars/primary/events?maxResults=15&orderBy=startTime&singleEvents=true&timeMin=" + new Date().toISOString(),
      {
        headers: {
          Authorization: "Bearer " + token,
        },
      }
    );

    if (!res.ok) {
      throw new Error(`Calendar API Error: ${res.status} ${res.statusText}`);
    }

    const data = await res.json();
    console.log("Calendar data received:", data);
    return data;
  } catch (err) {
    console.error("Calendar fetch error:", err);
    return { error: err.message, items: [] };
  }
}

// Fetch Gmail with full message details
async function fetchGmail() {
  try {
    const token = await getToken();
    console.log("Token received for Gmail");

    // First, get list of messages
    const listRes = await fetch(
      "https://www.googleapis.com/gmail/v1/users/me/messages?maxResults=10&q=is:unread",
      {
        headers: {
          Authorization: "Bearer " + token,
        },
      }
    );

    if (!listRes.ok) {
      throw new Error(`Gmail List Error: ${listRes.status} ${listRes.statusText}`);
    }

    const listData = await listRes.json();
    console.log("Gmail list data:", listData);

    if (!listData.messages || listData.messages.length === 0) {
      return { messages: [] };
    }

    // Now fetch full details for each message
    const messagePromises = listData.messages.slice(0, 8).map(msg =>
      fetch(`https://www.googleapis.com/gmail/v1/users/me/messages/${msg.id}?format=full`, {
        headers: {
          Authorization: "Bearer " + token,
        },
      })
        .then(res => res.json())
        .then(fullMsg => {
          const headers = fullMsg.payload?.headers || [];
          return {
            id: msg.id,
            subject: headers.find(h => h.name === "Subject")?.value || "(No Subject)",
            from: headers.find(h => h.name === "From")?.value || "Unknown",
            date: headers.find(h => h.name === "Date")?.value || "",
            snippet: fullMsg.snippet || "",
            payload: fullMsg.payload
          };
        })
        .catch(err => {
          console.error("Error fetching message:", err);
          return { id: msg.id, subject: "Error loading", from: "" };
        })
    );

    const messages = await Promise.all(messagePromises);
    console.log("Full email data received:", messages);
    return { messages };
  } catch (err) {
    console.error("Gmail fetch error:", err);
    return { error: err.message, messages: [] };
  }
}

// Message listener (MAIN BRIDGE)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "GET_DATA") {
    console.log("GET_DATA request received");
    Promise.all([fetchCalendar(), fetchGmail()])
      .then(([calendar, gmail]) => {
        console.log("Sending response:", { calendar, gmail });
        sendResponse({ calendar, gmail });
      })
      .catch((err) => {
        console.error("Error in message listener:", err);
        sendResponse({ error: err.toString(), calendar: { items: [] }, gmail: { messages: [] } });
      });

    return true;
  }
});