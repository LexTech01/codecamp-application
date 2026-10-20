/**
 * Blog detail: copy-link button (replaces inline onclick handler).
 */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".share-copy").forEach((btn) => {
    btn.addEventListener("click", () => {
      const icon = btn.querySelector("i");
      navigator.clipboard
        .writeText(window.location.href)
        .then(() => {
          if (icon) {
            icon.className = "fa-solid fa-check";
            setTimeout(() => {
              icon.className = "fa-solid fa-link";
            }, 2000);
          }
        })
        .catch(() => {});
    });
  });
});