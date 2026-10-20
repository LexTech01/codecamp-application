/**
 * Landing page: FAQ accordion.
 */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".faq-question").forEach((btn) => {
    btn.addEventListener("click", () => {
      const item = btn.closest(".faq-item");
      const isOpen = item && item.classList.contains("open");
      document
        .querySelectorAll(".faq-item.open")
        .forEach((el) => el.classList.remove("open"));
      if (item && !isOpen) item.classList.add("open");
    });
  });
});