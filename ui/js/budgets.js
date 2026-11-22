// The budgets page. It calls ONLY the Budgets & Alerts service (GET /budgets), which
// itself asks Subscriptions for the spending: the flow that crosses the seam on the server.
// If Subscriptions is down, Budgets still answers, with the budgets but without the spending.

let categories = [];

async function loadPage() {
  const page = document.getElementById("page");
  try {
    const data = (await api("budgets", "/budgets")).data;
    categories = data.categories;
    if (data.spending_available) {
      // One row per category that has spending or a budget (none yet = the empty card).
      page.innerHTML = data.rows.length ? drawStats(data.summary) + drawReport(data.rows) : drawEmpty();
    } else {
      showMessage("warning", escapeHtml(data.message));     // "Spending is unavailable right now..."
      page.innerHTML = drawBudgetsOnly(data.budgets);
    }
    page.innerHTML += drawBudgetForm();
    document.getElementById("budget-form").addEventListener("submit", saveBudget);
  } catch (error) {
    page.innerHTML = "";
    showProblem(error);
  }
}

function drawStats(summary) {
  const budget = summary.budget_total_cents
    ? `<span class="stat-value">${euros(summary.budget_total_cents)}</span>
       <span class="stat-hint">for the categories with a budget</span>`
    : `<span class="stat-value small">No budgets yet</span><span class="stat-hint">Set one below</span>`;
  const over = summary.over_budget.length
    ? `<span class="stat-value">${summary.over_budget.length}</span>
       <span class="stat-hint">${summary.over_budget.map(escapeHtml).join(", ")}</span>`
    : `<span class="stat-value small">None</span><span class="stat-hint">Every category is within budget</span>`;
  return `
    <section class="stats">
      <div class="stat stat-hero">
        <span class="stat-label">You spend per month</span>
        <span class="stat-value">${euros(summary.monthly_total_cents)}</span>
        <span class="stat-hint">${euros(summary.yearly_total_cents)} per year</span>
      </div>
      <div class="stat"><span class="stat-label">Monthly budget</span>${budget}</div>
      <div class="stat ${summary.over_budget.length ? "stat-alert" : ""}"><span class="stat-label">Over budget</span>${over}</div>
    </section>`;
}

function drawReport(rows) {
  return `
    <section class="card">
      <div class="list-head budget-row"><span>Category</span><span>Budget</span><span>Per month</span><span></span></div>
      ${rows.map(drawReportRow).join("")}
    </section>`;
}

function drawReportRow(row) {
  let progress;
  if (row.budget_cents) {
    let label = `${euros(row.budget_cents - row.monthly_cents)} left`;
    if (row.status === "over") label = `over by ${euros(row.monthly_cents - row.budget_cents)}`;
    if (row.status === "near") label = "close to the limit";
    progress = `
      <div class="bar"><span class="bar-fill status-${row.status}" style="width: ${Math.min(row.used_percent, 100)}%"></span></div>
      <span class="bar-label ${row.status}">${row.used_percent}% of ${euros(row.budget_cents)} · ${label}</span>
      <span class="muted date">Warns at ${row.warn_percent}%</span>`;
  } else {
    progress = `
      <div class="bar"><span class="bar-fill" style="width: ${row.share_percent}%"></span></div>
      <span class="bar-label">${row.share_percent}% of your spending · no budget</span>`;
  }
  const plural = row.count === 1 ? "" : "s";
  return `
    <div class="row budget-row cat-${categoryClass(row.category)}">
      <div class="row-main">
        <span class="avatar">${escapeHtml(row.category.charAt(0))}</span>
        <div>
          <div class="row-name">${escapeHtml(row.category)}</div>
          <span class="muted date">${row.count} subscription${plural}</span>
        </div>
      </div>
      <div class="budget-progress">${progress}</div>
      <div class="row-cell strong">
        <span class="cell-label">Per month</span>
        ${euros(row.monthly_cents)}
        <span class="muted date">${euros(row.yearly_cents)} / year</span>
      </div>
      <div class="row-actions">${row.budget_cents ? removeButton(row.category) : ""}</div>
    </div>`;
}

// Subscriptions is down: show only what Budgets knows by itself, its own budgets.
function drawBudgetsOnly(budgets) {
  const names = Object.keys(budgets);
  if (names.length === 0) {
    return "";
  }
  const rows = names.map((category) => `
    <div class="row budget-row cat-${categoryClass(category)}">
      <div class="row-main">
        <span class="avatar">${escapeHtml(category.charAt(0))}</span>
        <div class="row-name">${escapeHtml(category)}</div>
      </div>
      <div class="budget-progress"><span class="bar-label">Budget ${euros(budgets[category])} per month</span></div>
      <div class="row-cell muted">Spending unavailable</div>
      <div class="row-actions">${removeButton(category)}</div>
    </div>`).join("");
  return `<section class="card">${rows}</section>`;
}

function drawEmpty() {
  return `
    <section class="card empty">
      <div class="empty-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v9h9"/><circle cx="12" cy="12" r="9"/></svg></div>
      <h2>Nothing to add up yet</h2>
      <p>Add your subscriptions and SubTrack will show what each category costs you per month and per year.</p>
      <a class="button" href="subscription.html">Add a subscription</a>
    </section>`;
}

function removeButton(category) {
  const name = escapeHtml(category);
  return `
    <button class="icon-button danger" type="button" title="Remove the ${name} budget"
            onclick="removeBudget(this.dataset.category)" data-category="${name}">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M6 7l1 13h10l1-13"/><path d="M9 7V4h6v3"/></svg>
      <span class="sr-only">Remove budget</span>
    </button>`;
}

function drawBudgetForm() {
  const options = categories.map((category) => `<option>${escapeHtml(category)}</option>`).join("");
  return `
    <section class="card form budget-form">
      <div class="wide">
        <h2>Set a monthly budget</h2>
        <p class="subtitle">Pick a category and the most you want to spend on it per month.</p>
      </div>
      <form id="budget-form" class="budget-fields wide">
        <div class="field">
          <label for="category">Category</label>
          <select id="category" name="category">${options}</select>
        </div>
        <div class="field">
          <label for="amount">Budget per month</label>
          <div class="money"><span>€</span><input id="amount" name="amount" inputmode="decimal" placeholder="25" required></div>
        </div>
        <div class="field">
          <label for="warn_percent">Warn me at</label>
          <div class="money percent"><input id="warn_percent" name="warn_percent" inputmode="numeric" value="80" required><span>%</span></div>
        </div>
        <button type="submit" class="button">Save budget</button>
      </form>
      <small class="muted wide">A category can have one budget. Saving it again replaces the old amount and warning level.
        "Warn me at 80%" shows the category as close to the limit once you use 80% of its budget.</small>
    </section>`;
}

// Saving a budget only needs Budgets, so it works even when Subscriptions is down.
async function saveBudget(event) {
  event.preventDefault();
  const fields = event.target.elements;
  const values = {
    category: fields["category"].value,
    amount: fields["amount"].value,
    warn_percent: fields["warn_percent"].value,
  };
  await changeBudget("/budgets", values, `Budget for <strong>${escapeHtml(values.category)}</strong> saved.`);
}

async function removeBudget(category) {
  await changeBudget("/budgets/remove", { category }, `Budget for <strong>${escapeHtml(category)}</strong> removed.`);
}

async function changeBudget(path, values, doneMessage) {
  try {
    const result = await api("budgets", path, { method: "POST", json: values });
    if (!result.ok) {
      showErrors(result.data.errors);
      return;
    }
    await loadPage();
    if (!document.querySelector("#messages .warning")) {
      showMessage("success", doneMessage);
    }
    window.scrollTo(0, 0);
  } catch (error) {
    showProblem(error);
  }
}


// Start: everything above is defined, so the page can be drawn now.
requireLogin();
drawSidebar("budgets");
loadPage();
