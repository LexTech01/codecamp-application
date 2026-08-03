/**
 * Calendly-inspired interview scheduling
 */
document.addEventListener('DOMContentLoaded', () => {
  const schedulePage = document.querySelector('.interview-layout');
  if (!schedulePage) return;

  const state = {
    selectedDate: null,
    selectedSlotId: null,
    currentMonth: new Date(),
    availableDates: [],
  };

  const calendarGrid = document.getElementById('calendarGrid');
  const monthLabel = document.getElementById('monthLabel');
  const timeSlotsGrid = document.getElementById('timeSlotsGrid');
  const confirmBtn = document.getElementById('confirmBooking');
  const bookingPanel = document.getElementById('bookingPanel');
  const confirmPanel = document.getElementById('confirmPanel');

  init();

  async function init() {
    try {
      const data = await Cellusys.fetchJSON('/api/interview/available-dates');
      state.availableDates = data.dates || [];
      renderCalendar();
    } catch (e) {
      console.error(e);
      const panel = document.querySelector('.interview-calendar-panel');
      if (panel) {
        panel.innerHTML = '<div class="card" style="padding:40px;text-align:center"><p style="color:var(--error);margin-bottom:12px">Failed to load available dates.</p><button class="btn btn-primary" onclick="location.reload()">Try Again</button></div>';
      }
    }

    document.getElementById('prevMonth')?.addEventListener('click', () => {
      state.currentMonth.setMonth(state.currentMonth.getMonth() - 1);
      renderCalendar();
    });
    document.getElementById('nextMonth')?.addEventListener('click', () => {
      state.currentMonth.setMonth(state.currentMonth.getMonth() + 1);
      renderCalendar();
    });

    confirmBtn?.addEventListener('click', confirmBooking);
    document.getElementById('cancelBooking')?.addEventListener('click', cancelBooking);
    document.getElementById('rescheduleBooking')?.addEventListener('click', rescheduleBooking);
  }

  function renderCalendar() {
    const year = state.currentMonth.getFullYear();
    const month = state.currentMonth.getMonth();
    monthLabel.textContent = state.currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    let html = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
      .map(d => `<div class="cal-day-header">${d}</div>`).join('');

    for (let i = 0; i < firstDay; i++) html += '<div class="cal-day empty"></div>';

    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(year, month, day);
      const iso = date.toISOString().split('T')[0];
      const isAvailable = state.availableDates.includes(iso);
      const isPast = date < today;
      const isToday = date.getTime() === today.getTime();
      const isSelected = state.selectedDate === iso;

      let cls = 'cal-day';
      if (isPast || !isAvailable) cls += ' disabled';
      else cls += ' available';
      if (isToday) cls += ' today';
      if (isSelected) cls += ' selected';

      html += `<div class="${cls}" data-date="${iso}">${day}</div>`;
    }

    const monthPrefix = `${year}-${String(month + 1).padStart(2, '0')}`;
    const availableInMonth = state.availableDates.filter(d => d.startsWith(monthPrefix)).length;
    if (!availableInMonth) {
      html += '<div class="cal-empty">No availability this month yet. Please check back soon.</div>';
    }

    calendarGrid.innerHTML = html;

    calendarGrid.querySelectorAll('.cal-day.available').forEach(el => {
      el.addEventListener('click', () => selectDate(el.dataset.date));
    });
  }

  async function selectDate(dateStr) {
    state.selectedDate = dateStr;
    state.selectedSlotId = null;
    renderCalendar();
    timeSlotsGrid.innerHTML = '<div class="spinner" style="margin:20px auto"></div>';

    try {
      const data = await Cellusys.fetchJSON(`/api/interview/slots/${dateStr}`);
      if (!data.slots.length) {
        timeSlotsGrid.innerHTML = '<p class="text-muted">No slots available for this date.</p>';
        return;
      }
      timeSlotsGrid.innerHTML = data.slots.map(s => `
        <button type="button" class="time-slot-btn" data-slot-id="${s.id}">${s.label}</button>
      `).join('');

      timeSlotsGrid.querySelectorAll('.time-slot-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          timeSlotsGrid.querySelectorAll('.time-slot-btn').forEach(b => b.classList.remove('selected'));
          btn.classList.add('selected');
          state.selectedSlotId = parseInt(btn.dataset.slotId);
          confirmBtn.disabled = false;
        });
      });
    } catch (e) {
      timeSlotsGrid.innerHTML = '<p class="text-muted">Failed to load time slots.</p>';
    }
  }

  async function confirmBooking() {
    if (!state.selectedSlotId) return;
    confirmBtn.disabled = true;
    confirmBtn.textContent = 'Booking...';

    try {
      const result = await Cellusys.fetchJSON('/api/interview/book', {
        method: 'POST',
        body: JSON.stringify({ slot_id: state.selectedSlotId }),
      });
      if (bookingPanel) bookingPanel.classList.add('hidden');
      if (confirmPanel) {
        confirmPanel.classList.remove('hidden');
        document.getElementById('confirmDate').textContent = result.date;
        document.getElementById('confirmTime').textContent = result.time;
      }
    } catch (e) {
      alert('Booking failed. Please try another slot.');
      confirmBtn.disabled = false;
      confirmBtn.textContent = 'Confirm Booking';
    }
  }

  async function cancelBooking() {
    const bookingId = document.getElementById('cancelBooking')?.dataset.bookingId;
    if (!bookingId) return;
    const ok = await Cellusys.confirm('Cancel your interview?');
    if (!ok) return;
    await Cellusys.fetchJSON(`/api/interview/cancel/${bookingId}`, { method: 'POST' });
    location.reload();
  }

  async function rescheduleBooking() {
    const bookingId = document.getElementById('rescheduleBooking')?.dataset.bookingId;
    if (!bookingId) return;
    const ok = await Cellusys.confirm('Choose a new time? Your current slot will be freed.');
    if (!ok) return;
    await Cellusys.fetchJSON(`/api/interview/cancel/${bookingId}`, { method: 'POST' });
    location.reload();
  }
});
