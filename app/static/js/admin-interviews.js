/**
 * Admin interviews: toggle rejection reason on result, and slot mode forms.
 */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".booking-result").forEach((select) => {
    const toggle = () => {
      const reason = select.closest("form")?.querySelector(".booking-reason");
      if (reason) reason.style.display = select.value === "failed" ? "" : "none";
    };
    select.addEventListener("change", toggle);
    toggle();
  });

  const singleFields = document.getElementById("slot-fields-single");
  const recurringFields = document.getElementById("slot-fields-recurring");
  document.querySelectorAll(".slot-mode").forEach((radio) => {
    radio.addEventListener("change", () => {
      if (singleFields)
        singleFields.style.display = radio.value === "single" ? "" : "none";
      if (recurringFields)
        recurringFields.style.display = radio.value === "recurring" ? "" : "none";
    });
  });
});