/**
 * Student announcements page: auto-read + dismiss handlers.
 */
document.addEventListener("DOMContentLoaded", () => {
  const csrfToken =
    document.querySelector('meta[name="csrf-token"]')?.content || "";
  const csrfHeader = { "X-CSRFToken": csrfToken };

  const markRead = (card) => {
    fetch(`/api/announcements/${card.dataset.id}/read`, {
      method: "POST",
      headers: csrfHeader,
    }).catch(() => {});
  };

  const dismiss = (el) => {
    el.style.transition = "opacity 0.3s, transform 0.3s";
    el.style.opacity = "0";
    el.style.transform = "translateX(30px)";
    setTimeout(() => el.remove(), 300);
  };

  document.querySelectorAll(".announcement-card.unread").forEach(markRead);

  document.addEventListener("click", (e) => {
    const dismissBtn = e.target.closest(".announcement-dismiss");
    if (dismissBtn) {
      const card = dismissBtn.closest(".announcement-card");
      if (!card) return;
      fetch(`/api/announcements/${card.dataset.id}/read`, {
        method: "POST",
        headers: csrfHeader,
      }).catch(() => {});
      dismiss(card);
      return;
    }
    const updateBtn = e.target.closest(".update-dismiss");
    if (updateBtn) {
      const item = updateBtn.closest(".update-item");
      if (!item) return;
      fetch(`/api/notifications/${item.dataset.notifId}/read`, {
        method: "POST",
        headers: csrfHeader,
      }).catch(() => {});
      dismiss(item);
    }
  });
});