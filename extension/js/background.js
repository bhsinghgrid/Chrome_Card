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

// Send Meeting Invitation Email
async function sendMeetingInvite(to, subject, dateTime, duration, message) {
  try {
    const token = await getToken();
    
    // Create the email body
    const emailBody = `
Dear ${to.split('@')[0]},

${message}

Meeting Details:
- Date & Time: ${dateTime}
- Duration: ${duration} minutes
- Video Call: https://meet.google.com/new

Please click the link below to accept or decline this meeting:

ACCEPT: https://calendar.google.com/calendar/r/eventedit
DECLINE: https://calendar.google.com/calendar/r/eventedit

Best regards,
Your Colleague
    `;

    // Create raw message (base64 encoded email)
    const email = [
      'From: me',
      `To: ${to}`,
      `Subject: ${subject}`,
      'Content-Type: text/html; charset=utf-8',
      '',
      emailBody
    ].join('\n');

    const base64email = btoa(unescape(encodeURIComponent(email)));

    // Send via Gmail API
    const response = await fetch('https://www.googleapis.com/gmail/v1/users/me/messages/send', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        raw: base64email
      })
    });

    if (!response.ok) {
      throw new Error(`Gmail Send Error: ${response.status}`);
    }

    const result = await response.json();
    console.log('✅ Meeting invitation sent:', result);
    return { success: true, messageId: result.id };
  } catch (err) {
    console.error('❌ Error sending meeting invite:', err);
    return { success: false, error: err.message };
  }
}

// Create Calendar Event (ADD TO USER'S CALENDAR)
async function createCalendarEvent(title, description, startDateTime, endDateTime, guestEmail) {
  try {
    const token = await getToken();
    
    const event = {
      summary: title,
      description: description,
      start: {
        dateTime: startDateTime,
        timeZone: 'UTC'
      },
      end: {
        dateTime: endDateTime,
        timeZone: 'UTC'
      },
      attendees: [
        {
          email: guestEmail,
          responseStatus: 'needsAction'
        }
      ]
    };

    const response = await fetch('https://www.googleapis.com/calendar/v3/calendars/primary/events', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(event)
    });

    if (!response.ok) {
      throw new Error(`Calendar Create Error: ${response.status}`);
    }

    const result = await response.json();
    console.log('✅ Calendar event created:', result);
    return { success: true, eventId: result.id };
  } catch (err) {
    console.error('❌ Error creating calendar event:', err);
    return { success: false, error: err.message };
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
  } else if (message.type === "SEND_MEETING_INVITE") {
    console.log("SEND_MEETING_INVITE request received");
    const { to, subject, dateTime, duration, message: msg } = message;
    sendMeetingInvite(to, subject, dateTime, duration, msg)
      .then(result => sendResponse(result))
      .catch(err => sendResponse({ success: false, error: err.message }));
    
    return true;
  } else if (message.type === "CREATE_CALENDAR_EVENT") {
    console.log("CREATE_CALENDAR_EVENT request received");
    const { title, description, startDateTime, endDateTime, guestEmail } = message;
    createCalendarEvent(title, description, startDateTime, endDateTime, guestEmail)
      .then(result => sendResponse(result))
      .catch(err => sendResponse({ success: false, error: err.message }));
    
    return true;
  } else if (message.type === "OPEN_TAB") {
    console.log("OPEN_TAB request received:", message.url);
    chrome.tabs.create({ url: message.url }, (tab) => {
      console.log("New tab created:", tab.id);
      sendResponse({ success: true, tabId: tab.id });
    });
    return true;
  }
});