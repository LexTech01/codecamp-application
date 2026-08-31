/**
 * Sidebar toggle for mobile
 */
document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.querySelector(".sidebar");
  const overlay = document.querySelector(".sidebar-overlay");
  const toggleBtn = document.querySelector(".mobile-menu-btn");

  if (!sidebar) return;

  function openSidebar() {
    sidebar.classList.add("open");
    overlay?.classList.add("active");
    document.body.style.overflow = "hidden";
  }

  function closeSidebar() {
    sidebar.classList.remove("open");
    overlay?.classList.remove("active");
    document.body.style.overflow = "";
  }

  toggleBtn?.addEventListener("click", () => {
    sidebar.classList.contains("open") ? closeSidebar() : openSidebar();
  });

  overlay?.addEventListener("click", closeSidebar);

  document.querySelectorAll(".sidebar-link").forEach((link) => {
    link.addEventListener("click", () => {
      if (window.innerWidth <= 1024) closeSidebar();
    });
  });
});
