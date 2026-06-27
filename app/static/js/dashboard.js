/**
 * Dashboard-specific interactions and charts
 */
document.addEventListener('DOMContentLoaded', () => {
  initCharts();
  initCounterAnimation();
});

function initCharts() {
  const funnelCanvas = document.getElementById('funnelChart');
  const scoresCanvas = document.getElementById('scoresChart');
  const pipelineCanvas = document.getElementById('pipelineChart');

  if (typeof Chart === 'undefined') return;

  const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: '#9CA3AF', font: { family: 'Inter' } } } },
    scales: {
      x: { ticks: { color: '#9CA3AF' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      y: { ticks: { color: '#9CA3AF' }, grid: { color: 'rgba(255,255,255,0.05)' } },
    },
  };

  if (funnelCanvas) {
    const data = JSON.parse(funnelCanvas.dataset.values || '[]');
    const labels = JSON.parse(funnelCanvas.dataset.labels || '[]');
    new Chart(funnelCanvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Applicants',
          data,
          backgroundColor: 'rgba(255, 208, 0, 0.6)',
          borderColor: '#FFD000',
          borderWidth: 1,
          borderRadius: 8,
        }],
      },
      options: { ...chartDefaults, indexAxis: 'y' },
    });
  }

  if (scoresCanvas) {
    const data = JSON.parse(scoresCanvas.dataset.values || '[]');
    new Chart(scoresCanvas, {
      type: 'line',
      data: {
        labels: ['0-20', '21-40', '41-60', '61-80', '81-100'],
        datasets: [{
          label: 'Test Scores',
          data,
          borderColor: '#00C2FF',
          backgroundColor: 'rgba(0, 194, 255, 0.1)',
          fill: true,
          tension: 0.4,
        }],
      },
      options: chartDefaults,
    });
  }

  if (pipelineCanvas) {
    const data = JSON.parse(pipelineCanvas.dataset.values || '[]');
    const labels = JSON.parse(pipelineCanvas.dataset.labels || '[]');
    new Chart(pipelineCanvas, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data,
          backgroundColor: [
            'rgba(255, 208, 0, 0.8)',
            'rgba(0, 194, 255, 0.8)',
            'rgba(16, 185, 129, 0.8)',
            'rgba(245, 158, 11, 0.8)',
            'rgba(239, 68, 68, 0.8)',
            'rgba(156, 163, 175, 0.8)',
          ],
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'right', labels: { color: '#9CA3AF' } } },
      },
    });
  }
}

function initCounterAnimation() {
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = parseInt(el.dataset.count, 10);
    const duration = 1500;
    const start = performance.now();

    function update(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.floor(target * eased).toLocaleString();
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  });
}

// hero image slider
const slides = document.querySelectorAll(".slide");

let currentIndex = 0;

function changeSlide() {
    slides[currentIndex].classList.remove("active");

    currentIndex++;

    if (currentIndex >= slides.length) {
        currentIndex = 0;
    }

    slides[currentIndex].classList.add("active");
}

// Change image every 6 seconds
setInterval(changeSlide, 6000);