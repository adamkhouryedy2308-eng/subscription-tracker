// The bank import page. Step 1: upload a CSV and Subscriptions suggests the payments
// that repeat (the file is only read, never saved). Step 2: tick the ones to add.

let categories = [];
let suggestions = [];

function drawUploadForm() {
  document.getElementById("page").innerHTML = `
    <section class="card import-card">
      <p class="privacy-note">
        <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>
        <span>The file is read once and never saved. Only the subscriptions you confirm are stored.</span>
      </p>
      <form id="upload-form" class="import-form">
        <input type="file" name="statement" accept=".csv" required>
        <button type="submit" class="button">Find subscriptions</button>
      </form>
      <p class="muted date">
        A CSV export with the columns Date, Description and Amount. About 6 months works best.
        To try it, use <code>services/subscriptions/sample_data/bank_statement_example.csv</code> from the project.
      </p>
    </section>
    <div id="suggestions"></div>`;
  document.getElementById("upload-form").addEventListener("submit", upload);
}

async function upload(event) {
  event.preventDefault();
  const file = new FormData(event.target);       // the chosen file, sent like a normal upload
  try {
    const options = await api("subscriptions", "/subscriptions/options");
    categories = options.data.categories;
    const result = await api("subscriptions", "/subscriptions/import", { method: "POST", body: file });
    if (!result.ok) {
      document.getElementById("suggestions").innerHTML = "";
      showMessage("error", escapeHtml(result.data.errors[0]));
      return;
    }
    document.getElementById("messages").innerHTML = "";
    suggestions = result.data.suggestions;
    drawSuggestions(result.data);
  } catch (error) {
    showProblem(error);
  }
}

function drawSuggestions(data) {
  const plural = suggestions.length === 1 ? "" : "s";
  const skipped = data.skipped ? ` · ${data.skipped} rows could not be read` : "";
  let html = `
    <h2 class="import-summary">
      Found ${suggestions.length} subscription${plural}
      <span class="muted date">in ${data.payment_count} payments${skipped}</span>
    </h2>`;

  if (suggestions.length === 0) {
    html += `
      <section class="card empty">
        <h2>No repeating payments found</h2>
        <p>A subscription needs at least 3 payments with a regular rhythm. Try a statement that covers more months.</p>
      </section>`;
  } else {
    const rows = suggestions.map(drawSuggestion).join("");
    html += `
      <form id="confirm-form" class="card">
        ${rows}
        <div class="import-actions">
          <button type="submit" class="button">Add selected subscriptions</button>
        </div>
      </form>`;
  }
  document.getElementById("suggestions").innerHTML = html;
  const form = document.getElementById("confirm-form");
  if (form) {
    form.addEventListener("submit", confirmImport);
  }
}

// Row number i: a tick box and a category choice, unless it is already in the list.
function drawSuggestion(s, i) {
  const name = escapeHtml(s.name);
  const options = categories.map((category) =>
    `<option ${category === s.category ? "selected" : ""}>${escapeHtml(category)}</option>`).join("");
  const tick = s.already_tracked ? "<span></span>" : `<input type="checkbox" id="add-${i}" checked aria-label="Add ${name}">`;
  const category = s.already_tracked
    ? `<span class="chip">${escapeHtml(s.category)}</span>`
    : `<select id="category-${i}" aria-label="Category for ${name}">${options}</select>`;
  const tracked = s.already_tracked ? '<span class="badge trial">Already in your list</span>' : "";
  return `
    <div class="row import-row cat-${categoryClass(s.category)} ${s.already_tracked ? "tracked" : ""}">
      ${tick}
      <div class="row-main">
        <span class="avatar">${escapeHtml(s.name.charAt(0).toUpperCase())}</span>
        <div>
          <div class="row-name">${name} ${tracked}</div>
          <span class="muted date">${escapeHtml(s.bank_text)}</span>
        </div>
      </div>
      <div class="row-cell">${category}</div>
      <div class="row-cell strong">
        ${euros(s.amount_cents)}
        <span class="muted date">billed ${s.billing_cycle}</span>
      </div>
      <div class="row-cell">
        <span>Seen ${s.count} times</span>
        <span class="muted date">last on ${formatDate(s.last_payment_date)}</span>
      </div>
    </div>`;
}

// Send the ticked suggestions. The service checks each one like the add form does.
async function confirmImport(event) {
  event.preventDefault();
  const items = [];
  suggestions.forEach((s, i) => {
    const tick = document.getElementById(`add-${i}`);
    if (tick && tick.checked) {
      items.push({
        name: s.name,
        category: document.getElementById(`category-${i}`).value,
        price: (s.amount_cents / 100).toFixed(2),
        billing_cycle: s.billing_cycle,
        first_payment_date: s.last_payment_date,
      });
    }
  });
  try {
    const result = await api("subscriptions", "/subscriptions/import/confirm", { method: "POST", json: { items } });
    window.location.href = `subscriptions.html?imported=${result.data.added}`;
  } catch (error) {
    showProblem(error);
  }
}


// Start: everything above is defined, so the page can be drawn now.
requireLogin();
drawSidebar("import");
drawUploadForm();
