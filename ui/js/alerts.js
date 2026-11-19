// The alerts page: GET /alerts on Budgets & Alerts, which asks Subscriptions for the
// subscriptions. Without Subscriptions there are no alerts to work out: Budgets answers
// 503 with a clear message, and this page shows it.

const ALERT_ICONS = {
  trial_ending: '<path d="M6 2h12"/><path d="M6 22h12"/><path d="M7 2v4l5 6 5-6V2"/><path d="M7 22v-4l5-6 5 6v4"/>',
  over_budget: '<path d="M12 3l10 18H2z"/><path d="M12 10v4"/><path d="M12 17.5v.5"/>',
  price_rise: '<path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/>',
  payment_soon: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18"/><path d="M8 3v4"/><path d="M16 3v4"/>',
  unused: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
};

async function loadPage() {
  const page = document.getElementById("page");
  try {
    const result = await api("budgets", "/alerts");
    if (!result.ok) {
      page.innerHTML = "";
      showMessage("warning", escapeHtml(result.data.error));   // "Alerts are unavailable right now..."
      return;
    }
    const data = result.data;
    page.innerHTML = (data.alerts.length ? drawAlerts(data.alerts) : drawAllClear()) + drawRules(data);
  } catch (error) {
    page.innerHTML = "";
    showProblem(error);
  }
}

function drawAlerts(alerts) {
  return `<section class="alert-list">${alerts.map(drawAlert).join("")}</section>`;
}

function drawAlert(alert) {
  const name = `<strong>${escapeHtml(alert.name)}</strong>`;
  const amount = euros(alert.amount_cents);
  const texts = {
    trial_ending: ["Free trial ending", `${name} turns into a paid plan ${whenText(alert.days)}: you will be charged ${amount}.`],
    over_budget: ["Over budget", `${name} costs ${amount} a month, ${euros(alert.amount_cents - alert.limit_cents)} more than your ${euros(alert.limit_cents)} budget.`],
    price_rise: ["Price went up", `${name} went up from ${euros(alert.old_cents)} to ${amount} (+${alert.percent}%) on ${alert.date ? formatDate(alert.date, false) : ""}.`],
    payment_soon: ["Payment soon", `${name} charges ${amount} ${whenText(alert.days)}.`],
    unused: ["Not used for a while", `You have not used ${name} for ${alert.days} days but still pay ${amount} a month.`],
  };
  const [title, text] = texts[alert.kind];
  const link = alert.kind === "over_budget"
    ? '<a class="alert-action" href="budgets.html">See budget →</a>'
    : '<a class="alert-action" href="subscriptions.html">See subscription →</a>';
  return `
    <div class="card alert-card alert-${alert.kind}">
      <span class="alert-icon"><svg viewBox="0 0 24 24" aria-hidden="true">${ALERT_ICONS[alert.kind]}</svg></span>
      <div><h3>${title}</h3><p>${text}</p></div>
      ${link}
    </div>`;
}

function drawAllClear() {
  return `
    <section class="card empty">
      <div class="empty-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/></svg></div>
      <h2>All clear</h2>
      <p>No payments due soon, no free trials ending, nothing over budget and nothing you have stopped using.</p>
    </section>`;
}

function drawRules(data) {
  return `
    <p class="alert-rules">
      You get an alert when a payment is ${data.payment_soon_days} days away or less, a free trial ends within
      ${data.trial_warning_days} days, a category goes over its budget, a price went up in the last
      ${data.price_rise_days} days, or a subscription has not been used for ${data.unused_days} days.
    </p>`;
}


// Start: everything above is defined, so the page can be drawn now.
requireLogin();
drawSidebar("alerts");
loadPage();
