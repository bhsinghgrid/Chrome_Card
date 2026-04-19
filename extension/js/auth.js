async function login() {
  chrome.identity.getAuthToken({ interactive: true }, function(token) {
    chrome.storage.local.set({ token });
    console.log("Logged in", token);
  });
}

async function logout() {
  chrome.identity.clearAllCachedAuthTokens(() => {
    chrome.storage.local.remove("token");
  });
}

document.getElementById("login").addEventListener("click", login);
document.getElementById("logout").addEventListener("click", logout);