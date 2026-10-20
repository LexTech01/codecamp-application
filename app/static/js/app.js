/**
 * Cellusys Core UI — Premium interactions
 */
const Cellusys = {
  init() {
    this.initNavbar();
    this.initMobileNav();
    this.initImageFallbacks();
    this.initFlashMessages();
    this.initModals();
    this.initConfirmForms();
    this.initRippleEffect();
    this.initSmoothScroll();
    this.initPageEntrance();
    this.initPasswordToggle();
  },

  /* ── Navbar scroll effect ── */
  initNavbar() {
    const navbar = document.querySelector(".navbar");
    if (!navbar) return;
    const onScroll = () => {
      navbar.classList.toggle("scrolled", window.scrollY > 40);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  },

  /* ── Flash notification dropdowns ── */
  initFlashMessages() {
    const DURATION = 5000;
    document.querySelectorAll(".flash").forEach((el) => {
      let dismissed = false;

      const progress = el.querySelector(".flash-progress");
      if (progress) progress.style.animationDuration = `${DURATION}ms`;

      const dismiss = () => {
        if (dismissed) return;
        dismissed = true;
        el.classList.add("flash-hide");
        setTimeout(() => el.remove(), 400);
      };

      el.querySelector(".flash-close")?.addEventListener("click", dismiss);
      setTimeout(dismiss, DURATION);
    });
  },

  /* ── Mobile nav drawer (public pages: home, gallery, blog) ── */
  initMobileNav() {
    const btn = document.querySelector(".navbar-inner .mobile-menu-btn");
    const nav = document.querySelector(".nav-links");
    const overlay = document.querySelector(".nav-overlay");
    if (!btn || !nav) return;
    const openNav = () => {
      nav.classList.add("open");
      overlay?.classList.add("active");
      const icon = btn.querySelector("i");
      if (icon) icon.className = "fa-solid fa-xmark";
      document.body.style.overflow = "hidden";
    };
    const closeNav = () => {
      nav.classList.remove("open");
      overlay?.classList.remove("active");
      const icon = btn.querySelector("i");
      if (icon) icon.className = "fa-solid fa-bars";
      document.body.style.overflow = "";
    };
    btn.addEventListener("click", () => {
      nav.classList.contains("open") ? closeNav() : openNav();
    });
    nav.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeNav));
    overlay?.addEventListener("click", closeNav);
  },

  /* ── Image error fallbacks (replaces inline onerror handlers) ── */
  initImageFallbacks() {
    document.querySelectorAll("img[data-fallback-image]").forEach((img) => {
      img.addEventListener(
        "error",
        function handler() {
          img.removeEventListener("error", handler);
          const fallback = img.dataset.fallbackImage;
          if (fallback) img.src = fallback;
        },
        { once: true },
      );
    });
  },

  /* ── Modal overlay close ── */
  initModals() {
    document.addEventListener("click", (e) => {
      const overlay = e.target.closest(".modal-overlay");
      if (overlay && e.target === overlay) {
        overlay.classList.remove("active");
        document.body.style.overflow = "";
      }
    });
  },

  /* ── Confirmation modal for data-confirm forms ── */
  initConfirmForms() {
    document.addEventListener("submit", async (e) => {
      const form = e.target.closest("[data-confirm]");
      if (!form) return;
      e.preventDefault();
      const ok = await this.confirm(form.dataset.confirm);
      if (ok) form.submit();
    });
  },

  /* ── Date formatter ── */
  formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  },

  /* ── Fetch helper ── */
  async fetchJSON(url, options = {}) {
    const csrfToken = document
      .querySelector('meta[name="csrf-token"]')
      ?.getAttribute("content");
    const res = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken || "",
        ...options.headers,
      },
      ...options,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  /* ── Confirmation dialog ── */
  confirm(message) {
    return new Promise((resolve) => {
      const modal = document.getElementById("confirmModal");
      const msgEl = document.getElementById("confirmMessage");
      const okBtn = document.getElementById("confirmOk");
      const cancelBtn = document.getElementById("confirmCancel");
      if (!modal || !msgEl) {
        resolve(true);
        return;
      }

      msgEl.textContent = message;
      modal.classList.add("active");
      document.body.style.overflow = "hidden";

      const cleanup = () => {
        modal.classList.remove("active");
        document.body.style.overflow = "";
        okBtn.removeEventListener("click", onOk);
        cancelBtn.removeEventListener("click", onCancel);
        modal.removeEventListener("click", onOverlay);
      };

      const onOk = () => {
        cleanup();
        resolve(true);
      };
      const onCancel = () => {
        cleanup();
        resolve(false);
      };
      const onOverlay = (e) => {
        if (e.target === modal) {
          cleanup();
          resolve(false);
        }
      };

      okBtn.addEventListener("click", onOk);
      cancelBtn.addEventListener("click", onCancel);
      modal.addEventListener("click", onOverlay);
    });
  },

  /* ── Alert dialog (single OK button) ── */
  alert(message) {
    return new Promise((resolve) => {
      const modal = document.getElementById("confirmModal");
      const msgEl = document.getElementById("confirmMessage");
      const okBtn = document.getElementById("confirmOk");
      const cancelBtn = document.getElementById("confirmCancel");
      if (!modal || !msgEl) {
        resolve(true);
        return;
      }
      msgEl.textContent = message;
      cancelBtn.style.display = "none";
      okBtn.textContent = "OK";
      modal.classList.add("active");
      document.body.style.overflow = "hidden";

      const onOk = () => {
        cancelBtn.style.display = "";
        okBtn.textContent = "Confirm";
        modal.classList.remove("active");
        document.body.style.overflow = "";
        okBtn.removeEventListener("click", onOk);
        resolve(true);
      };
      const onOverlay = (e) => {
        if (e.target === modal) {
          cancelBtn.style.display = "";
          okBtn.textContent = "Confirm";
          modal.classList.remove("active");
          document.body.style.overflow = "";
          okBtn.removeEventListener("click", onOk);
          resolve(true);
        }
      };
      okBtn.addEventListener("click", onOk);
      modal.addEventListener("click", onOverlay);
    });
  },

  /* ── Ripple effect on buttons ── */
  initRippleEffect() {
    document.addEventListener("click", (e) => {
      const btn = e.target.closest(".btn");
      if (!btn) return;

      const existingRipple = btn.querySelector(".ripple-effect");
      if (existingRipple) existingRipple.remove();

      const rect = btn.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);

      const ripple = document.createElement("span");
      ripple.className = "ripple-effect";
      ripple.style.cssText = `
        position: absolute;
        border-radius: 50%;
        width: ${size}px;
        height: ${size}px;
        left: ${e.clientX - rect.left - size / 2}px;
        top: ${e.clientY - rect.top - size / 2}px;
        background: rgba(255,255,255,0.3);
        pointer-events: none;
        transform: scale(0);
        animation: ripple 0.6s ease-out;
      `;

      btn.style.position = btn.style.position || "relative";
      btn.style.overflow = btn.style.overflow || "hidden";
      btn.appendChild(ripple);

      setTimeout(() => ripple.remove(), 700);
    });
  },

  /* ── Smooth scroll for anchor links ── */
  initSmoothScroll() {
    document.addEventListener("click", (e) => {
      const link = e.target.closest('a[href^="#"]');
      if (!link) return;

      const targetId = link.getAttribute("href");
      if (targetId === "#") return;

      const target = document.querySelector(targetId);
      if (!target) return;

      e.preventDefault();
      const offset = 80;
      const top =
        target.getBoundingClientRect().top + window.pageYOffset - offset;

      window.scrollTo({
        top,
        behavior: "smooth",
      });
    });
  },

  /* ── Page entrance animation ── */
  initPageEntrance() {
    const mainContent = document.querySelector(".main-content");
    if (mainContent) {
      mainContent.classList.add("page-enter");
    }
  },

  /* ── Password visibility toggle ── */
  initPasswordToggle() {
    document.querySelectorAll(".password-toggle").forEach((btn) => {
      btn.addEventListener("click", () => {
        const input = btn
          .closest(".password-wrapper")
          .querySelector(".form-input");
        if (!input) return;
        const icon = btn.querySelector("i");
        if (input.type === "password") {
          input.type = "text";
          if (icon) icon.className = "fa-regular fa-eye-slash";
        } else {
          input.type = "password";
          if (icon) icon.className = "fa-regular fa-eye";
        }
      });
    });
  },
};

document.addEventListener("DOMContentLoaded", () => Cellusys.init());
