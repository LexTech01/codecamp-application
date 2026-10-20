/**
 * Admin cohorts: select-all, assign validation, and edit/notify toggles.
 */
document.addEventListener("DOMContentLoaded", () => {
  document
    .getElementById("select-all-unassigned")
    ?.addEventListener("change", function () {
      document
        .querySelectorAll(".unassigned-checkbox")
        .forEach((cb) => (cb.checked = this.checked));
    });

  document.getElementById("assign-form")?.addEventListener("submit", (e) => {
    const cohortSelect = document.getElementById("assign-cohort-select");
    if (!cohortSelect || !cohortSelect.value) {
      e.preventDefault();
      Cellusys.alert("Select a cohort to assign to.");
      return;
    }
    const checked = e.target.querySelectorAll(".unassigned-checkbox:checked");
    if (!checked.length) {
      e.preventDefault();
      Cellusys.alert("Select at least one student.");
    }
  });

  document.querySelectorAll("[data-toggle-target]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = document.getElementById(btn.dataset.toggleTarget);
      target?.classList.toggle("hidden");
    });
  });
});