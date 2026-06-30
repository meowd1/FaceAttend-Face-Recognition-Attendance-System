/* app.js — Shared JS: live clock, utility helpers */

/* ── Live Clock ─────────────────────────────────────── */
function updateClock() {
  const now = new Date();

  // Time — HH:MM:SS
  const h = String(now.getHours()).padStart(2, '0');
  const m = String(now.getMinutes()).padStart(2, '0');
  const s = String(now.getSeconds()).padStart(2, '0');
  const clockEl = document.getElementById('sidebar-clock');
  if (clockEl) clockEl.textContent = `${h}:${m}:${s}`;

  // Date — Weekday, DD Mon YYYY
  const days   = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const dateEl = document.getElementById('sidebar-date');
  if (dateEl) {
    dateEl.textContent = `${days[now.getDay()]}, ${now.getDate()} ${months[now.getMonth()]} ${now.getFullYear()}`;
  }
}

updateClock();
setInterval(updateClock, 1000);
