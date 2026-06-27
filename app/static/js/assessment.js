/**
 * Aptitude test interface with timer and auto-submit
 */
document.addEventListener('DOMContentLoaded', () => {
  const testEl = document.getElementById('assessmentTest');
  if (!testEl) return;

  const assessmentId = testEl.dataset.assessmentId;
  const durationMinutes = parseInt(testEl.dataset.duration || '45', 10);
  const dataEl = document.getElementById('questionsData');
  const questions = dataEl ? JSON.parse(dataEl.textContent) : [];

  let currentIndex = 0;
  const answers = {};
  let timeLeft = durationMinutes * 60;
  let timerInterval;

  // Anti-refresh warning
  var beforeUnloadHandler = function (e) {
    if (Object.keys(answers).length > 0 && timeLeft > 0) {
      e.preventDefault();
      e.returnValue = '';
    }
  };
  window.addEventListener('beforeunload', beforeUnloadHandler);

  initTimer();
  renderQuestion(0);
  renderQuestionNav();

  document.getElementById('prevQuestion')?.addEventListener('click', () => navigate(-1));
  document.getElementById('nextQuestion')?.addEventListener('click', () => {
    if (currentIndex === questions.length - 1) {
      submitTest();
    } else {
      navigate(1);
    }
  });
  document.getElementById('submitTest')?.addEventListener('click', async () => {
    const ok = await Cellusys.confirm('Submit your test? You cannot change answers after submission.');
    if (ok) submitTest();
  });

  function initTimer() {
    const timerEl = document.getElementById('timerValue');
    timerInterval = setInterval(() => {
      timeLeft--;
      const mins = Math.floor(timeLeft / 60);
      const secs = timeLeft % 60;
      timerEl.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

      if (timeLeft <= 300) timerEl.classList.add('warning');
      if (timeLeft <= 60) {
        timerEl.classList.remove('warning');
        timerEl.classList.add('danger');
      }
      if (timeLeft <= 0) {
        clearInterval(timerInterval);
        submitTest();
      }
    }, 1000);
  }

  function renderQuestion(index) {
    currentIndex = index;
    const q = questions[index];
    if (!q) return;

    document.getElementById('questionNumber').textContent = `Question ${index + 1} of ${questions.length}`;
    document.getElementById('questionText').textContent = q.text;
    document.getElementById('questionPoints').textContent = `${q.points} pts`;

    const optionsEl = document.getElementById('optionsList');
    optionsEl.innerHTML = q.options.map((opt, i) => `
      <div class="option-item ${answers[q.id] === i ? 'selected' : ''}" data-index="${i}">
        <div class="option-radio"></div>
        <span>${opt}</span>
      </div>
    `).join('');

    optionsEl.querySelectorAll('.option-item').forEach(item => {
      item.addEventListener('click', () => {
        answers[q.id] = parseInt(item.dataset.index);
        optionsEl.querySelectorAll('.option-item').forEach(o => o.classList.remove('selected'));
        item.classList.add('selected');
        renderQuestionNav();
      });
    });

    document.getElementById('prevQuestion').style.visibility = index === 0 ? 'hidden' : 'visible';
    document.getElementById('nextQuestion').innerHTML =
      index === questions.length - 1 ? 'Submit <i class="fa-solid fa-paper-plane"></i>' : 'Next <i class="fa-solid fa-arrow-right"></i>';

    document.querySelectorAll('.q-nav-btn').forEach((btn, i) => {
      btn.classList.toggle('current', i === index);
    });
  }

  function renderQuestionNav() {
    const nav = document.getElementById('questionNav');
    nav.innerHTML = questions.map((q, i) => {
      const answered = answers[q.id] !== undefined;
      return `<button type="button" class="q-nav-btn ${answered ? 'answered' : ''} ${i === currentIndex ? 'current' : ''}" data-index="${i}">${i + 1}</button>`;
    }).join('');

    nav.querySelectorAll('.q-nav-btn').forEach(btn => {
      btn.addEventListener('click', () => renderQuestion(parseInt(btn.dataset.index)));
    });

    const answered = Object.keys(answers).length;
    document.getElementById('progressText').textContent = `${answered}/${questions.length} answered`;
    document.getElementById('progressFill').style.width = `${(answered / questions.length) * 100}%`;
  }

  function navigate(dir) {
    const next = currentIndex + dir;
    if (next >= 0 && next < questions.length) renderQuestion(next);
  }

  async function submitTest() {
    clearInterval(timerInterval);
    window.removeEventListener('beforeunload', beforeUnloadHandler);
    const timeTaken = durationMinutes * 60 - timeLeft;

    try {
      const result = await Cellusys.fetchJSON(`/api/assessment/${assessmentId}/submit`, {
        method: 'POST',
        body: JSON.stringify({ answers, time_taken: timeTaken }),
      });
      window.location.href = `/student/assessment/result/${result.attempt_id}`;
    } catch (e) {
      alert('Submission failed. Please try again.');
    }
  }
});
