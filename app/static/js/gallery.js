/**
 * Gallery page: lightbox and category filter.
 */
document.addEventListener("DOMContentLoaded", () => {
  const lightbox = document.getElementById("galleryLightbox");
  const lightboxImg = document.getElementById("lightboxImage");
  const lightboxCaption = document.getElementById("lightboxCaption");
  const closeBtn = document.getElementById("lightboxClose");
  const prevBtn = document.getElementById("lightboxPrev");
  const nextBtn = document.getElementById("lightboxNext");
  if (!lightbox) return;

  const items = [];
  let currentIndex = 0;

  document.querySelectorAll(".gallery-item").forEach((item, index) => {
    const expandBtn = item.querySelector(".gallery-expand");
    items.push({
      src: expandBtn?.getAttribute("data-src") || "",
      alt: expandBtn?.getAttribute("data-alt") || "",
    });

    const onOpen = (e) => {
      if (e) e.stopPropagation();
      openLightbox(index);
    };
    expandBtn?.addEventListener("click", onOpen);
    item.addEventListener("click", onOpen);
  });

  function openLightbox(index) {
    currentIndex = index;
    updateLightbox();
    lightbox.classList.add("active");
    document.body.style.overflow = "hidden";
  }

  function updateLightbox() {
    const item = items[currentIndex];
    lightboxImg.src = item.src;
    lightboxImg.alt = item.alt;
    lightboxCaption.textContent = item.alt;
    prevBtn.style.display = items.length > 1 ? "" : "none";
    nextBtn.style.display = items.length > 1 ? "" : "none";
  }

  function closeLightbox() {
    lightbox.classList.remove("active");
    document.body.style.overflow = "";
  }

  function prevImage() {
    currentIndex = (currentIndex - 1 + items.length) % items.length;
    updateLightbox();
  }

  function nextImage() {
    currentIndex = (currentIndex + 1) % items.length;
    updateLightbox();
  }

  closeBtn?.addEventListener("click", closeLightbox);
  prevBtn?.addEventListener("click", prevImage);
  nextBtn?.addEventListener("click", nextImage);

  document.addEventListener("keydown", (e) => {
    if (!lightbox.classList.contains("active")) return;
    if (e.key === "Escape") closeLightbox();
    if (e.key === "ArrowLeft") prevImage();
    if (e.key === "ArrowRight") nextImage();
  });

  lightbox.addEventListener("click", (e) => {
    if (e.target === lightbox) closeLightbox();
  });

  /* ── Category filter ── */
  document.querySelectorAll(".gallery-filter").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".gallery-filter")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const filter = btn.getAttribute("data-filter");
      document.querySelectorAll(".gallery-item").forEach((item) => {
        const match =
          filter === "all" || item.getAttribute("data-category") === filter;
        item.style.display = match ? "" : "none";
      });
    });
  });
});