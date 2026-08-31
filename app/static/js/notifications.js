/**
 * Notification dropdown handling
 */
document.addEventListener("DOMContentLoaded", () => {
  const bell = document.querySelector(".notif-bell");
  const dropdown = document.querySelector(".notif-dropdown");

  if (!bell || !dropdown) return;

  bell.addEventListener("click", (e) => {
    e.stopPropagation();
    const mobile = window.matchMedia("(max-width: 1024px)").matches;
    const target = bell.dataset.notificationsHref;
    if (mobile && target) {
      window.location.href = target;
      return;
    }
    dropdown.classList.toggle("open");
    loadNotifications();
  });

  document.addEventListener("click", () => dropdown.classList.remove("open"));

  dropdown.addEventListener("click", (e) => e.stopPropagation());

  document
    .querySelector(".mark-all-read")
    ?.addEventListener("click", async (e) => {
      e.preventDefault();
      await Cellusys.fetchJSON("/api/notifications/read-all", {
        method: "POST",
      });
      document.querySelectorAll(".notif-item.unread").forEach((i) => {
        i.classList.remove("unread");
        i.classList.add("read");
      });
      const badge = document.querySelector(".notif-badge");
      if (badge) badge.style.display = "none";
    });

  async function loadNotifications() {
    const list = dropdown.querySelector(".notif-list");
    if (!list || list.dataset.loaded) return;
    try {
      const data = await Cellusys.fetchJSON("/api/notifications");
      list.innerHTML = data.length
        ? data
            .map(
              (n) => `
          <a href="${n.link || "#"}" class="notif-item ${n.is_read ? "read" : "unread"}"
             data-id="${n.id}">
            <div class="notif-item-dot"></div>
            <div class="notif-item-body">
              <div class="notif-item-title">${n.title}</div>
              <div class="notif-item-msg">${n.message || ""}</div>
              <div class="notif-item-time">${n.created_at}</div>
            </div>
          </a>`,
            )
            .join("")
        : '<div class="notif-empty">No notifications</div>';
      list.dataset.loaded = "true";
    } catch (err) {
      console.error("Failed to load notifications", err);
    }
  }
});
