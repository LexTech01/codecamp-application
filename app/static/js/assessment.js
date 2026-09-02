/**
 * Aptitude test interface with timer and auto-submit
 */
document.addEventListener("DOMContentLoaded", () => {
  const testEl = document.getElementById("assessmentTest");
  if (!testEl) return;

  const assessmentId = testEl.dataset.assessmentId;
  const durationMinutes = parseInt(testEl.dataset.duration || "20", 10);
  const dataEl = document.getElementById("questionsData");
  const questions = dataEl ? JSON.parse(dataEl.textContent) : [];

  // Persist progress so a page refresh resumes where the student left off.
  const storageKey = `cellusys_assessment_${assessmentId}`;
  let savedState = null;
  try {
    savedState = JSON.parse(localStorage.getItem(storageKey));
  } catch (e) {
    savedState = null;
  }

  const answers = (savedState && savedState.answers) || {};
  let currentIndex =
    typeof savedState?.currentIndex === "number" ? savedState.currentIndex : 0;
  let timeLeft =
    typeof savedState?.timeLeft === "number"
      ? savedState.timeLeft
      : durationMinutes * 60;
  const savedAt =
    typeof savedState?.savedAt === "number" ? savedState.savedAt : null;
  if (savedAt) {
    // Adjust for the wall-clock time that elapsed while away from the page.
    timeLeft = Math.max(
      0,
      timeLeft - Math.floor((Date.now() - savedAt) / 1000),
    );
  }
  let timerInterval;
  let submitting = false;

  function persistState() {
    try {
      localStorage.setItem(
        storageKey,
        JSON.stringify({
          answers,
          currentIndex,
          timeLeft,
          savedAt: Date.now(),
        }),
      );
    } catch (e) {
      /* storage unavailable - ignore */
    }
  }

  function clearState() {
    try {
      localStorage.removeItem(storageKey);
    } catch (e) {
      /* ignore */
    }
  }

  // Anti-refresh warning
  var beforeUnloadHandler = function (e) {
    if (Object.keys(answers).length > 0 && timeLeft > 0) {
      e.preventDefault();
      e.returnValue = "";
    }
  };
  window.addEventListener("beforeunload", beforeUnloadHandler);

  initTimer();
  renderQuestion(Math.min(currentIndex, questions.length - 1));
  renderQuestionNav();

  const onPrev = () => navigate(-1);
  const onNext = () => {
    if (currentIndex === questions.length - 1) {
      submitTest();
    } else {
      navigate(1);
    }
  };
  const onNextPlain = () => navigate(1);
  const onSubmitClick = async () => {
    const ok = await Cellusys.confirm(
      "Submit your test? You cannot change answers after submission.",
    );
    if (ok) {
      submitting = true;
      submitTest();
    }
  };

  document.getElementById("prevQuestion")?.addEventListener("click", onPrev);
  document.getElementById("nextQuestion")?.addEventListener("click", onNext);
  document
    .getElementById("prevQuestionMobile")
    ?.addEventListener("click", onPrev);
  document
    .getElementById("nextQuestionMobile")
    ?.addEventListener("click", onNextPlain);
  document
    .getElementById("submitTest")
    ?.addEventListener("click", onSubmitClick);
  document
    .getElementById("submitTestMobile")
    ?.addEventListener("click", onSubmitClick);

  // Keyboard navigation: arrows move between questions, number keys jump to a question.
  document.addEventListener("keydown", (e) => {
    if (e.target.matches("input, textarea, select")) return;
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      navigate(-1);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      onNext();
    } else if (
      e.key === "1" ||
      e.key === "2" ||
      e.key === "3" ||
      e.key === "4" ||
      e.key === "5" ||
      e.key === "6" ||
      e.key === "7" ||
      e.key === "8" ||
      e.key === "9"
    ) {
      const idx = parseInt(e.key, 10) - 1;
      if (idx < questions.length) renderQuestion(idx);
    }
  });

  function initTimer() {
    const timerEl = document.getElementById("timerValue");
    timerInterval = setInterval(() => {
      timeLeft--;
      const mins = Math.floor(timeLeft / 60);
      const secs = timeLeft % 60;
      timerEl.textContent = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;

      if (timeLeft <= 300) timerEl.classList.add("warning");
      if (timeLeft <= 60) {
        timerEl.classList.remove("warning");
        timerEl.classList.add("danger");
      }
      if (timeLeft <= 0) {
        clearInterval(timerInterval);
        submitTest();
      } else {
        persistState();
      }
    }, 1000);
  }

  function renderQuestion(index) {
    currentIndex = index;
    const q = questions[index];
    if (!q) return;

    document.getElementById("questionNumber").textContent =
      `Question ${index + 1} of ${questions.length}`;
    document.getElementById("questionText").textContent = q.text;
    document.getElementById("questionPoints").textContent = `${q.points} pts`;

    const qImgWrap = document.getElementById("questionImageWrap");
    if (qImgWrap) {
      qImgWrap.innerHTML = "";
      if (q.image) {
        const img = document.createElement("img");
        img.src = q.image;
        img.alt = "Question image";
        img.className = "question-image";
        qImgWrap.appendChild(img);
      }
    }

    const optionsEl = document.getElementById("optionsList");
    optionsEl.innerHTML = "";
    q.options.forEach((opt, i) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = `option-item ${answers[q.id] === i ? "selected" : ""}`;
      item.dataset.index = i;
      item.setAttribute("aria-pressed", String(answers[q.id] === i));

      const radio = document.createElement("span");
      radio.className = "option-radio";
      item.appendChild(radio);

      const body = document.createElement("span");
      body.className = "option-body";

      const optImg = q.option_images && q.option_images[i];
      if (optImg) {
        const img = document.createElement("img");
        img.src = optImg;
        img.alt = `Option ${String.fromCharCode(65 + i)}`;
        img.className = "option-image";
        img.loading = "lazy";
        body.appendChild(img);
      }
      if (opt) {
        const span = document.createElement("span");
        span.className = "option-label";
        span.textContent = opt;
        body.appendChild(span);
      }
      item.appendChild(body);

      item.addEventListener("click", () => {
        answers[q.id] = parseInt(item.dataset.index, 10);
        optionsEl.querySelectorAll(".option-item").forEach((o) => {
          o.classList.remove("selected");
          o.setAttribute("aria-pressed", "false");
        });
        item.classList.add("selected");
        item.setAttribute("aria-pressed", "true");
        renderQuestionNav();
        persistState();
      });
      optionsEl.appendChild(item);
    });

    const isFirst = index === 0;
    ["prevQuestion", "prevQuestionMobile"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.style.visibility = isFirst ? "hidden" : "visible";
    });
    const isLast = index === questions.length - 1;
    const nextBtn = document.getElementById("nextQuestion");
    const nextMobile = document.getElementById("nextQuestionMobile");
    const submitMobile = document.getElementById("submitTestMobile");
    if (nextBtn) {
      nextBtn.innerHTML = isLast
        ? 'Submit <i class="fa-solid fa-paper-plane"></i>'
        : 'Next <i class="fa-solid fa-arrow-right"></i>';
    }
    if (nextMobile) {
      nextMobile.style.display = isLast ? "none" : "";
      submitMobile.style.display = isLast ? "" : "none";
    }

    document.querySelectorAll(".q-nav-btn").forEach((btn, i) => {
      btn.classList.toggle("current", i === index);
    });
    persistState();

    // Bring the question into view (important on small screens).
    const main = document.querySelector(".assessment-main");
    if (main && window.innerWidth <= 900) {
      main.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function renderQuestionNav() {
    const nav = document.getElementById("questionNav");
    nav.innerHTML = questions
      .map((q, i) => {
        const answered = answers[q.id] !== undefined;
        return `<button type="button" class="q-nav-btn ${answered ? "answered" : ""} ${i === currentIndex ? "current" : ""}" data-index="${i}">${i + 1}</button>`;
      })
      .join("");

    nav.querySelectorAll(".q-nav-btn").forEach((btn) => {
      btn.addEventListener("click", () =>
        renderQuestion(parseInt(btn.dataset.index)),
      );
    });

    const answered = Object.keys(answers).length;
    document.getElementById("progressText").textContent =
      `${answered}/${questions.length} answered`;
    document.getElementById("progressFill").style.width =
      `${(answered / questions.length) * 100}%`;
  }

  function navigate(dir) {
    const next = currentIndex + dir;
    if (next >= 0 && next < questions.length) renderQuestion(next);
  }

  async function submitTest() {
    if (submitting) return;
    submitting = true;
    clearInterval(timerInterval);
    window.removeEventListener("beforeunload", beforeUnloadHandler);
    const timeTaken = durationMinutes * 60 - timeLeft;

    try {
      const result = await Cellusys.fetchJSON(
        `/api/assessment/${assessmentId}/submit`,
        {
          method: "POST",
          body: JSON.stringify({ answers, time_taken: timeTaken }),
        },
      );
      clearState();
      window.location.href = `/student/assessment/result/${result.attempt_id}`;
    } catch (e) {
      Cellusys.alert("Submission failed. Please try again.");
    }
  }
});
