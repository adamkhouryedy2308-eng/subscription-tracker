// Shared helpers for every page: the login token, calling the two services,
// the side menu, messages, and showing money and dates.
// Every page loads config.js first (the services' addresses), then this file, then its own script.

const SERVICES = {
  subscriptions: { name: "Subscriptions", url: window.SUBTRACK_CONFIG.subscriptionsUrl },
  budgets: { name: "Budgets & Alerts", url: window.SUBTRACK_CONFIG.budgetsUrl },
};

// A sleeping service on Azure can need about a minute to wake up (cold start),
// so a call that gets no real answer is tried again: 4 tries, 5 seconds apart.
const ATTEMPTS = 4;
const WAIT_SECONDS = 5;
const TOKEN_KEY = "subtrack_token";


// ---------- The login token (kept in this browser only) ----------

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function saveToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function logOut() {
  localStorage.removeItem(TOKEN_KEY);
  window.location.href = "login.html";
}

// Pages that need a login send visitors without a token to the login page.
function requireLogin() {
  if (!getToken()) {
    window.location.href = "login.html";
  }
}


// ---------- Calling a service ----------

// Thrown when a service gives no real answer, even after waiting for it to wake up.
class ServiceDown extends Error {
  constructor(service) {
    super(`The ${SERVICES[service].name} service is not answering right now. ` +
          "It may be starting up: try again in a minute.");
  }
}

// Call one of the two services and return { status, ok, data }.
//   service: "subscriptions" or "budgets"
//   options.method: "GET" (default), "POST" or "PUT"
//   options.json: an object to send as JSON
//   options.body: something else to send, e.g. an uploaded file (FormData)
//   options.quiet: true = try only once and show no "starting up" message
async function api(service, path, options = {}) {
  const headers = {};
  let body = options.body;
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  }
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const attempts = options.quiet ? 1 : ATTEMPTS;
  for (let attempt = 1; attempt <= attempts; attempt++) {
    let response = null;
    try {
      response = await fetch(SERVICES[service].url + path, { method: options.method || "GET", headers, body });
    } catch (noAnswer) {
      response = null;   // the service is stopped, asleep, or the browser blocked the call
    }
    const data = response ? await readJson(response) : null;

    // Our services always answer in JSON, even for errors. No answer, or a 502/503/504
    // that is not JSON, comes from Azure while the container is still starting.
    const stillStarting = response === null || ([502, 503, 504].includes(response.status) && data === null);
    if (!stillStarting) {
      if (!options.quiet) {
        hideWaitMessage();   // quiet calls (the side menu) never touch the waiting message
      }
      if (response.status === 401 && token) {
        logOut();          // the token is too old (7 days) or not valid: log in again
      }
      return { status: response.status, ok: response.ok, data };
    }
    if (attempt < attempts) {
      showWaitMessage(service, attempt, attempts);
      await sleep(WAIT_SECONDS * 1000);
    }
  }
  if (!options.quiet) {
    hideWaitMessage();
  }
  throw new ServiceDown(service);
}

async function readJson(response) {
  try {
    return await response.json();
  } catch (notJson) {
    return null;
  }
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}


// ---------- Messages at the top of the page ----------

const ICONS = {
  success: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/></svg>',
  error: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v6"/><path d="M12 16.5v.5"/></svg>',
  warning: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
};

// kind: "success", "error" or "warning". html must already be escaped.
function showMessage(kind, html) {
  document.getElementById("messages").innerHTML =
    `<div class="notice ${kind}">${ICONS[kind]}<div>${html}</div></div>`;
}

// A list of errors from a service, e.g. ["Enter a name."]
function showErrors(errors) {
  const items = errors.map((error) => `<li>${escapeHtml(error)}</li>`).join("");
  const title = errors.length === 1 ? "Please fix this:" : `Please fix these ${errors.length} things:`;
  showMessage("error", `<strong>${title}</strong><ul>${items}</ul>`);
}

// What the user sees when a call failed: a clear message and a "Try again" button.
function showProblem(error) {
  const text = error instanceof ServiceDown ? error.message : "Something went wrong. Try again in a minute.";
  document.getElementById("messages").innerHTML =
    `<div class="notice warning">${ICONS.warning}<div>${escapeHtml(text)}</div>` +
    '<button class="button ghost" type="button" onclick="window.location.reload()">Try again</button></div>';
}

function showWaitMessage(service, attempt, attempts) {
  let box = document.getElementById("wait-message");
  if (!box) {
    box = document.createElement("div");
    box.id = "wait-message";
    box.className = "notice warning";
    document.getElementById("messages").before(box);
  }
  box.innerHTML = `${ICONS.warning}<div>The ${SERVICES[service].name} service is starting up. ` +
    `Trying again in ${WAIT_SECONDS} seconds (${attempt} of ${attempts - 1})…</div>`;
}

function hideWaitMessage() {
  const box = document.getElementById("wait-message");
  if (box) {
    box.remove();
  }
}


// ---------- Showing values ----------

// Text typed by users (names, emails) is escaped before it goes into the page,
// so a name like <script> is shown as text and never runs.
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  return div.innerHTML;
}

// 1349 -> "€13.49"
function euros(cents) {
  return new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR" }).format(cents / 100);
}

// "2026-01-15" -> "15 Jan 2026"
function formatDate(isoDate, withYear = true) {
  const options = withYear ? { day: "2-digit", month: "short", year: "numeric" } : { day: "2-digit", month: "short" };
  return new Date(isoDate + "T00:00:00").toLocaleDateString("en-GB", options);
}

// 0 -> "today", 1 -> "tomorrow", 5 -> "in 5 days"
function whenText(days) {
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  return `in ${days} days`;
}

function capitalise(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

// "Food & Delivery" -> "food-delivery", the colour class used by style.css
function categoryClass(category) {
  return category.toLowerCase().replace(" & ", "-").replace(/ /g, "-");
}

// A value from the address bar, e.g. ?id=3 -> getParam("id") = "3"
function getParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}


// ---------- The side menu (on every page after login) ----------

const MENU = [
  { page: "subscriptions", label: "Subscriptions",
    icon: '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 10h18"/><path d="M7 15h4"/>' },
  { page: "subscription", label: "Add subscription",
    icon: '<circle cx="12" cy="12" r="9"/><path d="M12 8v8"/><path d="M8 12h8"/>' },
  { page: "import", label: "Import from bank",
    icon: '<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>' },
  { page: "budgets", label: "Budgets",
    icon: '<path d="M12 3v9h9"/><circle cx="12" cy="12" r="9"/>' },
  { page: "alerts", label: "Alerts",
    icon: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>' },
];

function drawSidebar(activePage) {
  const links = MENU.map((item) =>
    `<a class="nav-link ${item.page === activePage ? "active" : ""}" href="${item.page}.html" id="nav-${item.page}">` +
    `<svg viewBox="0 0 24 24" aria-hidden="true">${item.icon}</svg>${item.label}</a>`).join("");

  document.getElementById("sidebar").innerHTML = `
    <a class="brand" href="subscriptions.html">
      <span class="brand-mark">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17 2l4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15"/><path d="M7 22l-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/></svg>
      </span>
      <span class="brand-name">SubTrack</span>
    </a>
    <nav class="nav">${links}</nav>
    <p class="sidebar-note">Know what you pay for.<br>Keep what you use.</p>
    <div class="user-box">
      <span class="user-avatar" id="user-avatar">·</span>
      <span class="user-email" id="user-email"></span>
      <button class="icon-button" type="button" title="Log out" onclick="logOut()">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3"/><path d="M10 17l-5-5 5-5"/><path d="M5 12h11"/></svg>
        <span class="sr-only">Log out</span>
      </button>
    </div>`;

  fillUserBox();
  fillAlertBadge();
}

// The email comes from Subscriptions. If it is down, the menu simply stays without it.
async function fillUserBox() {
  try {
    const result = await api("subscriptions", "/me", { quiet: true });
    if (result.ok) {
      document.getElementById("user-email").textContent = result.data.email;
      document.getElementById("user-avatar").textContent = result.data.email.charAt(0).toUpperCase();
    }
  } catch (serviceDown) {
    // nothing to show
  }
}

// The number next to "Alerts" comes from Budgets & Alerts (which asks Subscriptions).
async function fillAlertBadge() {
  try {
    const result = await api("budgets", "/alerts", { quiet: true });
    if (result.ok && result.data.alerts.length > 0) {
      const count = result.data.alerts.length;
      document.getElementById("nav-alerts").insertAdjacentHTML("beforeend",
        `<span class="nav-badge" title="${count} alerts">${count}</span>`);
    }
  } catch (serviceDown) {
    // no badge
  }
}
