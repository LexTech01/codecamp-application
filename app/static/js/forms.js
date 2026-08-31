/**
 * Multi-step application form wizard
 */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("applicationForm");
  if (!form) return;

  let currentStep = parseInt(
    document.getElementById("current_step")?.value || "1",
    10,
  );
  const totalSteps = 2;
  form.noValidate = true;

  showStep(currentStep);

  document.getElementById("wizardNext")?.addEventListener("click", (e) => {
    e.preventDefault();
    if (validateStep(currentStep)) {
      if (currentStep < totalSteps) {
        currentStep++;
        showStep(currentStep);
        updateIndicators();
      }
    }
  });

  document.getElementById("wizardPrev")?.addEventListener("click", (e) => {
    e.preventDefault();
    if (currentStep > 1) {
      currentStep--;
      showStep(currentStep);
      updateIndicators();
    }
  });

  form?.addEventListener("submit", (e) => {
    for (let step = 1; step <= totalSteps; step++) {
      if (!validateStep(step)) {
        e.preventDefault();
        currentStep = step;
        showStep(currentStep);
        updateIndicators();
        return;
      }
    }
  });

  form.querySelectorAll("input, select").forEach((field) => {
    const eventName = field.type === "radio" ? "change" : "input";
    field.addEventListener(eventName, () => {
      if (field.type === "radio") {
        clearFieldError(field.name);
        form
          .querySelectorAll(`input[type="radio"][name="${field.name}"]`)
          .forEach((radio) => {
            radio.closest(".selection-card")?.classList.remove("input-error");
          });
        return;
      }
      if (
        field.value.trim() &&
        (field.type !== "email" || field.checkValidity())
      ) {
        field.style.borderColor = "";
        clearFieldError(field.name);
      }
    });
  });

  function showStep(step) {
    document
      .querySelectorAll(".wizard-panel")
      .forEach((p) => p.classList.remove("active"));
    document.getElementById(`step${step}`)?.classList.add("active");
    document.getElementById("current_step").value = step;
    const prevBtn = document.getElementById("wizardPrev");
    const nextBtn = document.getElementById("wizardNext");
    const submitBtn = document.getElementById("wizardSubmit");
    if (prevBtn) prevBtn.style.visibility = step === 1 ? "hidden" : "visible";
    if (nextBtn)
      nextBtn.style.display = step < totalSteps ? "inline-flex" : "none";
    if (submitBtn)
      submitBtn.style.display = step === totalSteps ? "inline-flex" : "none";
    updateIndicators();
  }

  function updateIndicators() {
    document.querySelectorAll(".wizard-step-indicator").forEach((ind, i) => {
      const stepNum = i + 1;
      ind.classList.remove("active", "done");
      if (stepNum < currentStep) ind.classList.add("done");
      if (stepNum === currentStep) ind.classList.add("active");
    });
  }

  function validateStep(step) {
    const panel = document.getElementById(`step${step}`);
    const required = panel?.querySelectorAll("[required]") || [];
    let valid = true;
    const checkedRadioGroups = new Set();
    for (const field of required) {
      const fieldLabel =
        field
          .closest(".form-group")
          ?.querySelector(".form-label")
          ?.textContent.trim() || "This field";
      if (field.type === "radio") {
        if (checkedRadioGroups.has(field.name)) continue;
        checkedRadioGroups.add(field.name);
        const selected = panel.querySelector(
          `input[type="radio"][name="${field.name}"]:checked`,
        );
        if (!selected) {
          valid = false;
          setFieldError(
            field.name,
            `Please select ${fieldLabel.toLowerCase()}.`,
          );
          panel
            .querySelectorAll(`input[type="radio"][name="${field.name}"]`)
            .forEach((radio) => {
              radio.closest(".selection-card")?.classList.add("input-error");
            });
        } else {
          clearFieldError(field.name);
          panel
            .querySelectorAll(`input[type="radio"][name="${field.name}"]`)
            .forEach((radio) => {
              radio.closest(".selection-card")?.classList.remove("input-error");
            });
        }
        continue;
      }
      if (!field.value.trim()) {
        field.style.borderColor = "var(--error)";
        setFieldError(field.name, `${fieldLabel} is required.`);
        valid = false;
      } else if (field.type === "email" && !field.checkValidity()) {
        field.style.borderColor = "var(--error)";
        setFieldError(field.name, "Please enter a valid email address.");
        valid = false;
      } else {
        field.style.borderColor = "";
        clearFieldError(field.name);
      }
    }
    return valid;
  }

  function setFieldError(name, message) {
    const error = document.querySelector(`[data-error-for="${name}"]`);
    if (!error) return;
    error.textContent = message;
    error.classList.add("visible");
  }

  function clearFieldError(name) {
    const error = document.querySelector(`[data-error-for="${name}"]`);
    if (!error) return;
    error.textContent = "";
    error.classList.remove("visible");
  }
});
