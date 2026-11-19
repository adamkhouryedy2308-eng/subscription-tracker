// The login page: send the email and password to Subscriptions, keep the token it gives back.

if (getToken()) {
  window.location.href = "subscriptions.html";   // already logged in
}

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();                         // stay on this page: we send the form ourselves
  const fields = event.target.elements;   // the form's inputs, by their name
  try {
    const result = await api("subscriptions", "/login", {
      method: "POST",
      json: { email: fields["email"].value, password: fields["password"].value },
    });
    if (result.ok) {
      saveToken(result.data.token);
      window.location.href = "subscriptions.html";
    } else {
      showMessage("error", escapeHtml(result.data.error));   // "Wrong email or password."
    }
  } catch (error) {
    showProblem(error);
  }
});
