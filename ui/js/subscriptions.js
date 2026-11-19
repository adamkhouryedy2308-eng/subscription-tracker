// The subscriptions page: totals, every active subscription, and the cancelled ones.
// All of it comes from the Subscriptions service: GET /subscriptions.

// After saving, other pages come back here with e.g. ?added=Netflix in the address.
const NOTICES = {
  added: "was added to your subscriptions.",
  updated: "was updated.",
  cancelled: "was cancelled. You can still see it under Cancelled.",
  imported: "subscriptions were added from your bank statement.",
};

function showNoticeFromAddress() {
  for (const [action, text] of Object.entries(NOTICES)) {
    const name = getParam(action);
    if (name) {
      showMessage("success", `<strong>${escapeHtml(name)}</strong> ${text}`);
    }
  }
}

async function loadPage() {
  const page = document.getElementById("page");
  try {
    const result = await api("subscriptions", "/subscriptions");
    const data = result.data;
    if (data.subscriptions.length === 0) {
      page.innerHTML = drawEmpty();
    } else {
      page.innerHTML = drawStats(data.summary) + drawList(data.subscriptions);
    }
    if (data.cancelled.length > 0) {
      page.innerHTML += drawCancelled(data.cancelled, data.yearly_savings_cents);
    }
  } catch (error) {
    page.innerHTML = "";
    showProblem(error);
  }
}

function drawStats(summary) {
  const next = summary.next_up;
  const plural = summary.count === 1 ? "" : "s";
  return `
    <section class="stats">
      <div class="stat stat-hero">
        <span class="stat-label">You spend per month</span>
        <span class="stat-value">${euros(summary.monthly_total_cents)}</span>
        <span class="stat-hint">across ${summary.count} subscription${plural}</span>
      </div>
      <div class="stat">
        <span class="stat-label">Per year</span>
        <span class="stat-value">${euros(summary.yearly_total_cents)}</span>
        <span class="stat-hint">if nothing changes</span>
      </div>
      <div class="stat">
        <span class="stat-label">Next payment</span>
        <span class="stat-value small">${escapeHtml(next.name)}</span>
        <span class="stat-hint">${euros(next.price_cents)} · ${whenText(next.days_until_payment)}</span>
      </div>
    </section>`;
}

function drawList(subscriptions) {
  const rows = subscriptions.map(drawRow).join("");
  return `
    <section class="card">
      <div class="list-head">
        <span>Subscription</span><span>Price</span><span>Per month</span><span>Next payment</span><span></span>
      </div>
      ${rows}
    </section>`;
}

function drawRow(sub) {
  const name = escapeHtml(sub.name);
  let badges = sub.is_trial ? '<span class="badge trial">Free trial</span>' : "";
  const was = `Was ${euros(sub.original_price_cents)} when you subscribed`;
  if (sub.price_change_percent > 0) {
    badges += `<span class="badge price-up" title="${was}">▲ ${sub.price_change_percent}%</span>`;
  } else if (sub.price_change_percent < 0) {
    badges += `<span class="badge price-down" title="${was}">▼ ${-sub.price_change_percent}%</span>`;
  }
  return `
    <div class="row cat-${categoryClass(sub.category)}">
      <div class="row-main">
        <span class="avatar">${escapeHtml(sub.name.charAt(0).toUpperCase())}</span>
        <div>
          <div class="row-name">${name} ${badges}</div>
          <span class="chip">${escapeHtml(sub.category)}</span>
        </div>
      </div>
      <div class="row-cell">
        <span class="cell-label">Price</span>
        ${euros(sub.price_cents)}
        <span class="muted date">billed ${sub.billing_cycle}</span>
      </div>
      <div class="row-cell strong">
        <span class="cell-label">Per month</span>
        ${euros(sub.monthly_cost_cents)}
      </div>
      <div class="row-cell">
        <span class="cell-label">Next payment</span>
        <span class="when ${sub.days_until_payment <= 3 ? "soon" : ""}">${capitalise(whenText(sub.days_until_payment))}</span>
        <span class="muted date">${formatDate(sub.next_payment_date)}</span>
      </div>
      <div class="row-actions">
        <a class="icon-button" href="subscription.html?id=${sub.id}" title="Edit ${name}">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16v4z"/><path d="M13.5 6.5l4 4"/></svg>
          <span class="sr-only">Edit</span>
        </a>
        <button class="icon-button danger" type="button" title="Cancel ${name}"
                onclick="cancelSubscription(${sub.id}, this)" data-name="${name}">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M9 9l6 6"/><path d="M15 9l-6 6"/></svg>
          <span class="sr-only">Cancel</span>
        </button>
      </div>
    </div>`;
}

function drawEmpty() {
  return `
    <section class="card empty">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="2" y="5" width="20" height="14" rx="3"/><path d="M2 10h20"/><path d="M6 15h4"/></svg>
      </div>
      <h2>No subscriptions yet</h2>
      <p>Add Netflix, Spotify, your gym or anything else you pay for regularly, and SubTrack will show what it really costs you.</p>
      <a class="button" href="subscription.html">Add your first subscription</a>
    </section>`;
}

function drawCancelled(cancelled, yearlySavingsCents) {
  const rows = cancelled.map((sub) => `
    <div class="row row-cancelled cat-${categoryClass(sub.category)}">
      <div class="row-main">
        <span class="avatar">${escapeHtml(sub.name.charAt(0).toUpperCase())}</span>
        <div>
          <div class="row-name">${escapeHtml(sub.name)}</div>
          <span class="chip">${escapeHtml(sub.category)}</span>
        </div>
      </div>
      <div class="row-cell">
        <span class="cell-label">Cancelled</span>
        <span class="muted">Cancelled ${formatDate(sub.cancelled_date)}</span>
      </div>
      <div class="row-cell strong saving">
        <span class="cell-label">Saving</span>
        ${euros(sub.yearly_saving_cents)} / year
      </div>
    </div>`).join("");
  return `
    <section class="cancelled">
      <div class="section-head">
        <h2>Cancelled</h2>
        <span class="savings">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/></svg>
          You're saving <strong>${euros(yearlySavingsCents)}</strong> a year
        </span>
      </div>
      <div class="card">${rows}</div>
    </section>`;
}

// The button keeps the (escaped) name in data-name, so the question can use it.
async function cancelSubscription(id, button) {
  const name = button.dataset.name;
  if (!confirm(`Cancel ${name}? It will move to your cancelled list.`)) {
    return;
  }
  try {
    const result = await api("subscriptions", `/subscriptions/${id}/cancel`, { method: "POST" });
    if (result.ok) {
      window.location.href = `subscriptions.html?cancelled=${encodeURIComponent(result.data.name)}`;
    } else {
      showMessage("error", escapeHtml(result.data.error));
    }
  } catch (error) {
    showProblem(error);
  }
}


// Start: everything above is defined, so the page can be drawn now.
requireLogin();
drawSidebar("subscriptions");
showNoticeFromAddress();
loadPage();
