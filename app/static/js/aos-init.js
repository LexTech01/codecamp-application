/**
 * AOS scroll-reveal initialization (externalized so script-src can drop
 * 'unsafe-inline').
 */
document.addEventListener("DOMContentLoaded", () => {
  if (typeof AOS !== "undefined") {
    AOS.init({
      duration: 800,
      offset: 60,
      once: false,
      mirror: true,
    });
  }
});