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
      if (!data.length) {
        const empty = document.createElement("div");
        empty.className = "notif-empty";
        empty.textContent = "No notifications";
        list.appendChild(empty);
        list.dataset.loaded = "true";
        return;
      }
      data.forEach((n) => {
        const item = document.createElement("a");
        const link = n.link || "#";
        item.href = link.startsWith("/") || link === "#" ? link : "#";
        item.className = `notif-item ${n.is_read ? "read" : "unread"}`;
        item.dataset.id = n.id;

        const dot = document.createElement("div");
        dot.className = "notif-item-dot";

        const body = document.createElement("div");
        body.className = "notif-item-body";

        const title = document.createElement("div");
        title.className = "notif-item-title";
        title.textContent = n.title || "";

        const msg = document.createElement("div");
        msg.className = "notif-item-msg";
        msg.textContent = n.message || "";

        const time = document.createElement("div");
        time.className = "notif-item-time";
        time.textContent = n.created_at;

        body.append(title, msg, time);
        item.append(dot, body);
        list.appendChild(item);
      });
      list.dataset.loaded = "true";
    } catch (err) {
      console.error("Failed to load notifications", err);
    }
  }
});
