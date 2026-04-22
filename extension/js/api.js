async function getToken() {
  return new Promise(resolve => {
    chrome.storage.local.get(["token"], res => resolve(res.token));
  });
}

async function fetchCalendar() {
  const token = await getToken();
  const res = await fetch("https://www.googleapis.com/calendar/v3/calendars/primary/events?maxResults=10&orderBy=startTime&singleEvents=true", {
    headers: { Authorization: "Bearer " + token }
  });
  return res.json();
}

async function fetchGmail() {
  const token = await getToken();
  const res = await fetch("https://www.googleapis.com/gmail/v1/users/me/messages?maxResults=10", {
    headers: { Authorization: "Bearer " + token }
  });
  return res.json();
}