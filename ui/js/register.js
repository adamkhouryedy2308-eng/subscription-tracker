// The sign-up page: create the account on Subscriptions, which logs you in straight away.

if (getToken()) {
  window.location.href = "subscriptions.html";   // already logged in
}

document.getElementById("register-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const fields = event.target.elements;   // the form's inputs, by their name
  try {
    const result = await api("subscriptions", "/register", {
      method: "POST",
      json: {
        email: fields["email"].value,
        password: fields["password"].value,
        confirm_password: fields["confirm_password"].value,
      },
    });
    if (result.ok) {
      saveToken(result.data.token);
      window.location.href = "subscriptions.html";
    } else {
      showErrors(result.data.errors);              // e.g. "This email already has an account."
    }
  } catch (error) {
    showProblem(error);
  }
});
