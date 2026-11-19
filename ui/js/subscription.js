// The add / edit form. subscription.html adds a new subscription;
// subscription.html?id=3 edits subscription 3. Both talk to the Subscriptions service.

const subscriptionId = getParam("id");   // null when adding

async function loadPage() {
  const page = document.getElementById("page");
  try {
    // The choices for the form (10 categories, 4 billing cycles) come from the service.
    const options = (await api("subscriptions", "/subscriptions/options")).data;
    let values = { billing_cycle: "monthly" };
    let history = [];
    if (subscriptionId) {
      const result = await api("subscriptions", `/subscriptions/${subscriptionId}`);
      if (!result.ok) {
        page.innerHTML = "";
        showMessage("error", escapeHtml(result.data.error));   // "Subscription not found."
        return;
      }
      values = result.data.form;
      history = result.data.history;
      document.getElementById("title").textContent = `Edit ${values.name}`;
      document.getElementById("subtitle").textContent = "Change what you need and save.";
      document.title = `Edit ${values.name} · SubTrack`;
    }
    page.innerHTML = drawForm(options, values) + drawHistory(history);
    document.getElementById("subscription-form").addEventListener("submit", save);
  } catch (error) {
    page.innerHTML = "";
    showProblem(error);
  }
}

function drawForm(options, values) {
  const value = (name) => escapeHtml(values[name] || "");
  const categories = options.categories.map((category) =>
    `<option ${category === values.category ? "selected" : ""}>${escapeHtml(category)}</option>`).join("");
  const cycles = options.billing_cycles.map((cycle) => `
    <label class="pill">
      <input type="radio" name="billing_cycle" value="${cycle}" ${cycle === values.billing_cycle ? "checked" : ""}>
      <span>${capitalise(cycle)}</span>
    </label>`).join("");

  return `
    <form id="subscription-form" class="card form">
      <div class="field wide">
        <label for="name">Name</label>
        <input id="name" name="name" value="${value("name")}" maxlength="100"
               placeholder="e.g. Netflix, Spotify, Gym" required autofocus>
      </div>
      <div class="field">
        <label for="category">Category</label>
        <select id="category" name="category">${categories}</select>
      </div>
      <div class="field">
        <label for="price">Price</label>
        <div class="money">
          <span>€</span>
          <input id="price" name="price" value="${value("price")}" inputmode="decimal" placeholder="9.99" required>
        </div>
      </div>
      <fieldset class="field wide">
        <legend>How often do you pay?</legend>
        <div class="pills">${cycles}</div>
      </fieldset>
      <div class="field">
        <label for="first_payment_date">First payment date</label>
        <input id="first_payment_date" type="date" name="first_payment_date" value="${value("first_payment_date")}" required>
        <small>For a free trial: the day the trial ends.</small>
      </div>
      <div class="field">
        <label for="last_used_date">Last used <span class="optional">optional</span></label>
        <input id="last_used_date" type="date" name="last_used_date" value="${value("last_used_date")}">
        <small>Helps SubTrack spot things you no longer use.</small>
      </div>
      <label class="toggle wide">
        <input type="checkbox" name="is_trial" ${values.is_trial === "on" ? "checked" : ""}>
        <span class="switch"></span>
        <span>
          <strong>This is a free trial</strong>
          <small>We'll remind you before it turns into a paid plan.</small>
        </span>
      </label>
      <div class="actions wide">
        <a class="button ghost" href="subscriptions.html">Back</a>
        <button type="submit" class="button">Save subscription</button>
      </div>
    </form>`;
}

function drawHistory(history) {
  if (history.length === 0) {
    return "";
  }
  const rows = history.slice().reverse().map((change) => {
    const up = change.percent > 0;
    return `
      <div class="history-row">
        <span class="muted">${formatDate(change.changed_date)}</span>
        <span>${euros(change.old_price_cents)} → <strong>${euros(change.new_price_cents)}</strong></span>
        <span class="badge ${up ? "price-up" : "price-down"}">${up ? "▲" : "▼"} ${Math.abs(change.percent)}%</span>
      </div>`;
  }).join("");
  return `<section class="card history-card"><h2>Price history</h2>${rows}</section>`;
}

// Send the form as JSON: POST to add, PUT to save changes. The service checks every value.
async function save(event) {
  event.preventDefault();
  const fields = event.target.elements;          // the form's inputs, by their name
  const values = {
    name: fields["name"].value,
    category: fields["category"].value,
    price: fields["price"].value,
    billing_cycle: fields["billing_cycle"].value,  // the ticked radio button
    first_payment_date: fields["first_payment_date"].value,
    last_used_date: fields["last_used_date"].value,
    is_trial: fields["is_trial"].checked ? "on" : "",
  };
  const path = subscriptionId ? `/subscriptions/${subscriptionId}` : "/subscriptions";
  try {
    const result = await api("subscriptions", path, { method: subscriptionId ? "PUT" : "POST", json: values });
    if (result.ok) {
      const action = subscriptionId ? "updated" : "added";
      window.location.href = `subscriptions.html?${action}=${encodeURIComponent(values.name.trim())}`;
    } else {
      showErrors(result.data.errors || [result.data.error]);
      window.scrollTo(0, 0);
    }
  } catch (error) {
    showProblem(error);
  }
}


// Start: everything above is defined, so the page can be drawn now.
requireLogin();
drawSidebar(subscriptionId ? "subscriptions" : "subscription");   // editing belongs to the list
loadPage();
