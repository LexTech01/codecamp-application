/**
 * Landing page: FAQ accordion.
 */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".faq-question").forEach((btn) => {
    btn.addEventListener("click", () => {
      const item = btn.closest(".faq-item");
      const isOpen = item && item.classList.contains("open");
      document
        .querySelectorAll(".faq-item.open")
        .forEach((el) => el.classList.remove("open"));
      if (item && !isOpen) item.classList.add("open");
    });
  });

  document.querySelectorAll("[data-program-carousel]").forEach((carousel) => {
    const viewport = carousel.querySelector("[data-program-viewport]");
    const track = carousel.querySelector("[data-program-track]");
    const slides = Array.from(carousel.querySelectorAll("[data-program-slide]"));
    const previousButton = carousel.querySelector("[data-program-prev]");
    const nextButton = carousel.querySelector("[data-program-next]");
    const currentCount = carousel.querySelector("[data-program-current]");
    const totalCount = carousel.querySelector("[data-program-total]");

    if (
      !viewport ||
      !track ||
      slides.length === 0 ||
      !previousButton ||
      !nextButton ||
      !currentCount ||
      !totalCount
    ) {
      return;
    }

    let activeIndex = 0;
    let pointerStart = null;
    let suppressClick = false;

    const updateCarousel = () => {
      const firstSlideOffset = slides[0].offsetLeft;
      const activeSlideOffset = slides[activeIndex].offsetLeft;
      track.style.transform = `translateX(-${activeSlideOffset - firstSlideOffset}px)`;

      slides.forEach((slide, index) => {
        const title = slide.querySelector("h3")?.textContent.trim();
        slide.setAttribute(
          "aria-label",
          `${index + 1} of ${slides.length}${title ? `: ${title}` : ""}`,
        );
        slide.setAttribute("aria-hidden", String(index !== activeIndex));
        slide.inert = index !== activeIndex;
      });

      currentCount.textContent = String(activeIndex + 1).padStart(2, "0");
      totalCount.textContent = String(slides.length).padStart(2, "0");
      previousButton.disabled = activeIndex === 0;
      nextButton.disabled = activeIndex === slides.length - 1;
    };

    const goToSlide = (index) => {
      activeIndex = Math.max(0, Math.min(index, slides.length - 1));
      updateCarousel();
    };

    previousButton.addEventListener("click", () => goToSlide(activeIndex - 1));
    nextButton.addEventListener("click", () => goToSlide(activeIndex + 1));

    viewport.addEventListener("keydown", (event) => {
      if (event.target.closest("a, button, input, select, textarea")) return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        goToSlide(activeIndex - 1);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        goToSlide(activeIndex + 1);
      }
    });

    viewport.addEventListener("pointerdown", (event) => {
      if (event.pointerType === "mouse" && event.button !== 0) return;
      pointerStart = { x: event.clientX, y: event.clientY };
    });

    viewport.addEventListener("pointerup", (event) => {
      if (!pointerStart) return;
      const deltaX = event.clientX - pointerStart.x;
      const deltaY = event.clientY - pointerStart.y;
      pointerStart = null;

      if (Math.abs(deltaX) < 45 || Math.abs(deltaX) < Math.abs(deltaY)) return;
      goToSlide(activeIndex + (deltaX < 0 ? 1 : -1));
      suppressClick = true;
      window.setTimeout(() => {
        suppressClick = false;
      }, 350);
    });

    viewport.addEventListener("pointercancel", () => {
      pointerStart = null;
    });

    viewport.addEventListener(
      "click",
      (event) => {
        if (!suppressClick) return;
        event.preventDefault();
        event.stopPropagation();
        suppressClick = false;
      },
      true,
    );

    window.addEventListener("resize", updateCarousel, { passive: true });
    updateCarousel();
  });
});