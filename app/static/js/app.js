/**
 * Core application utilities
 */
const Cellusys = {
  init() {
    this.initNavbar();
    this.initFlashMessages();
    this.initRevealAnimations();
    this.initModals();
    this.initConfirmForms();
  },

  initNavbar() {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;
    const onScroll = () => {
      navbar.classList.toggle('scrolled', window.scrollY > 40);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  },

  initFlashMessages() {
    document.querySelectorAll('.flash').forEach(el => {
      setTimeout(() => {
        el.style.opacity = '0';
        el.style.transform = 'translateX(40px)';
        setTimeout(() => el.remove(), 400);
      }, 5000);
    });
  },

  initRevealAnimations() {
    const reveals = document.querySelectorAll('.reveal');
    if (!reveals.length) return;
    const observer = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    );
    reveals.forEach(el => observer.observe(el));
  },

  initModals() {
    document.addEventListener('click', e => {
      const openBtn = e.target.closest('[data-modal-open]');
      const closeBtn = e.target.closest('[data-modal-close]');
      const overlay = e.target.closest('.modal-overlay');

      if (openBtn) {
        const id = openBtn.dataset.modalOpen;
        document.getElementById(id)?.classList.add('active');
      }
      if (closeBtn || (overlay && e.target === overlay)) {
        document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
      }
    });
  },

  initConfirmForms() {
    document.addEventListener('submit', async e => {
      const form = e.target.closest('[data-confirm]');
      if (!form) return;
      e.preventDefault();
      const ok = await this.confirm(form.dataset.confirm);
      if (ok) form.submit();
    });
  },

  formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('en-US', {
      weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
    });
  },

  async fetchJSON(url, options = {}) {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  confirm(message) {
    return new Promise(resolve => {
      const modal = document.getElementById('confirmModal');
      const msgEl = document.getElementById('confirmMessage');
      const okBtn = document.getElementById('confirmOk');
      const cancelBtn = document.getElementById('confirmCancel');
      if (!modal || !msgEl) { resolve(true); return; }
      msgEl.textContent = message;
      modal.classList.add('active');
      const cleanup = () => {
        modal.classList.remove('active');
        okBtn.removeEventListener('click', onOk);
        cancelBtn.removeEventListener('click', onCancel);
        modal.removeEventListener('click', onOverlay);
      };
      const onOk = () => { cleanup(); resolve(true); };
      const onCancel = () => { cleanup(); resolve(false); };
      const onOverlay = e => { if (e.target === modal) { cleanup(); resolve(false); } };
      okBtn.addEventListener('click', onOk);
      cancelBtn.addEventListener('click', onCancel);
      modal.addEventListener('click', onOverlay);
    });
  },
};

document.addEventListener('DOMContentLoaded', () => Cellusys.init());
