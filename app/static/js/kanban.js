/**
 * Drag-and-drop Kanban recruitment board
 */
document.addEventListener("DOMContentLoaded", () => {
  const board = document.querySelector(".kanban-board");
  if (!board) return;
  if (board.dataset.readonly === "true") return;

  let draggedCard = null;
  let originalParent = null;
  let originalNextSibling = null;

  document.querySelectorAll(".kanban-card").forEach((card) => {
    card.setAttribute("draggable", "true");

    card.addEventListener("dragstart", (e) => {
      draggedCard = card;
      originalParent = card.parentElement;
      originalNextSibling = card.nextElementSibling;
      card.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", card.dataset.appId);
    });

    card.addEventListener("dragend", () => {
      card.classList.remove("dragging");
      draggedCard = null;
      originalParent = null;
      originalNextSibling = null;
    });
  });

  document.querySelectorAll(".kanban-cards").forEach((column) => {
    column.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      column.style.background = "rgba(255, 208, 0, 0.05)";
    });

    column.addEventListener("dragleave", () => {
      column.style.background = "";
    });

    column.addEventListener("drop", async (e) => {
      e.preventDefault();
      column.style.background = "";
      if (!draggedCard) return;

      const appId = draggedCard.dataset.appId;
      const movedCard = draggedCard;
      const columnKey = column.closest(".kanban-column").dataset.column;
      const originalColumnKey =
        originalParent?.closest(".kanban-column")?.dataset.column;

      if (columnKey === originalColumnKey) return;

      column.appendChild(movedCard);
      updateColumnCounts();

      try {
        await Cellusys.fetchJSON("/api/pipeline/move", {
          method: "POST",
          body: JSON.stringify({
            application_id: parseInt(appId),
            column: columnKey,
          }),
        });
      } catch (err) {
        console.error("Failed to move card", err);
        if (originalParent) {
          originalParent.insertBefore(movedCard, originalNextSibling);
          updateColumnCounts();
        }
        alert("That move is not allowed for this applicant stage.");
      }
    });
  });

  function updateColumnCounts() {
    document.querySelectorAll(".kanban-column").forEach((col) => {
      const count = col.querySelectorAll(".kanban-card").length;
      const badge = col.querySelector(".kanban-count");
      if (badge) badge.textContent = count;
    });
  }
});
