//Main JS for fact.check authentication page

document.addEventListener("DOMContentLoaded", function() {
   initializePage();
});

function initializePage() {
    const continue_btn = document.getElementById("continue-btn");
    const email = document.getElementById("email");
    const password = document.getElementById("password");

    continue_btn.addEventListener("click", function () {
        console.log("User Credentials: " + email.value + " " + password.value);
    });
}
