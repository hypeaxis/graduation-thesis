/* ===================================================================
   IDS Dashboard — Application Logic
   =================================================================== */

// ─── Severity Config ────────────────────────────────────────────────
const SEVERITY_MAP = {
  Normal: { css: 'normal', color: '#2dd4a8', bg: 'rgba(45,212,168,0.12)' },
  DoS:    { css: 'dos',    color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
  Probe:  { css: 'probe',  color: '#3b82f6', bg: 'rgba(59,130,246,0.12)' },
  R2L:    { css: 'r2l',    color: '#f97316', bg: 'rgba(249,115,22,0.12)' },
  U2R:    { css: 'u2r',    color: '#ef4444', bg: 'rgba(239,68,68,0.12)' },
};

const CHART_COLORS = ['#2dd4a8', '#f59e0b', '#3b82f6', '#f97316', '#ef4444'];

// ─── State ──────────────────────────────────────────────────────────
const state = {
  lastSimulation: null,
  sessionHistory: [],
  donutChart: null,
  lineChart: null,
};

// ─── DOM Cache ──────────────────────────────────────────────────────
const dom = {
  apiStatus: document.getElementById('apiStatus'),
  apiStatusText: document.getElementById('apiStatusText'),
  headerClock: document.getElementById('headerClock'),
  scenario: document.getElementById('scenario'),
  totalEvents: document.getElementById('totalEvents'),
  benignRatio: document.getElementById('benignRatio'),
  windowSeconds: document.getElementById('windowSeconds'),
  simulateBtn: document.getElementById('simulateBtn'),
  detectLatestBtn: document.getElementById('detectLatestBtn'),
  simulateDetectBtn: document.getElementById('simulateDetectBtn'),
  simMeta: document.getElementById('simMeta'),
  detectMeta: document.getElementById('detectMeta'),
  alertPreviewBody: document.getElementById('alertPreviewBody'),
  predictionBody: document.getElementById('predictionBody'),
  detectionTiles: document.getElementById('detectionTiles'),
  toastContainer: document.getElementById('toastContainer'),
  statTotal: document.getElementById('statTotal'),
  statAttacks: document.getElementById('statAttacks'),
  statNormal: document.getElementById('statNormal'),
  statConfidence: document.getElementById('statConfidence'),
  donutCanvas: document.getElementById('donutChart'),
  lineCanvas: document.getElementById('lineChart'),
};

// ─── Utilities ──────────────────────────────────────────────────────
function escapeHtml(raw) {
  return String(raw)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function numberVal(el, fallback) {
  const v = Number(el.value);
  return Number.isFinite(v) ? v : fallback;
}

function requestPayload() {
  return {
    scenario: dom.scenario.value,
    total_events: numberVal(dom.totalEvents, 120),
    benign_ratio: numberVal(dom.benignRatio, 0.35),
    window_seconds: numberVal(dom.windowSeconds, 2),
  };
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `Request failed: ${response.status}`);
  }
  return data;
}

function severityOf(label) {
  return SEVERITY_MAP[label] || SEVERITY_MAP.Normal;
}

// ─── Clock ──────────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  dom.headerClock.textContent = now.toLocaleTimeString('en-GB', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}
setInterval(updateClock, 1000);
updateClock();

// ─── Toast ──────────────────────────────────────────────────────────
function showToast(message, { icon = '🔔', danger = false, duration = 4000 } = {}) {
  const toast = document.createElement('div');
  toast.className = `toast${danger ? ' toast-danger' : ''}`;
  toast.innerHTML = `<span class="toast-icon">${icon}</span>${escapeHtml(message)}`;
  dom.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('toast-out');
    toast.addEventListener('animationend', () => toast.remove());
  }, duration);
}

// ─── Animated Counter ───────────────────────────────────────────────
function animateValue(el, target, { duration = 600, decimals = 0, suffix = '' } = {}) {
  const start = parseFloat(el.textContent) || 0;
  if (start === target) { el.textContent = target.toFixed(decimals) + suffix; return; }
  const startTime = performance.now();

  function tick(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    const current = start + (target - start) * eased;
    el.textContent = current.toFixed(decimals) + suffix;
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

// ─── API Health ─────────────────────────────────────────────────────
async function checkHealth() {
  try {
    await api('/api/health');
    dom.apiStatus.classList.remove('offline');
    dom.apiStatusText.textContent = 'Online';
  } catch {
    dom.apiStatus.classList.add('offline');
    dom.apiStatusText.textContent = 'Offline';
  }
}
checkHealth();
setInterval(checkHealth, 30000);

// ─── Busy State ─────────────────────────────────────────────────────
function setBusy(isBusy) {
  dom.simulateBtn.disabled = isBusy;
  dom.simulateDetectBtn.disabled = isBusy;
  dom.detectLatestBtn.disabled = isBusy || !state.lastSimulation;

  if (isBusy) {
    dom.simulateDetectBtn.innerHTML = '<span class="spinner"></span> Processing…';
  } else {
    dom.simulateDetectBtn.innerHTML = '<span class="btn-icon">🚀</span> Simulate + Detect';
  }
}

// ─── Render: Alert Preview ──────────────────────────────────────────
function renderAlerts(previewRows = []) {
  if (!previewRows.length) {
    dom.alertPreviewBody.innerHTML = '<tr class="empty-row"><td colspan="6">No alerts — run a simulation first</td></tr>';
    return;
  }

  dom.alertPreviewBody.innerHTML = previewRows
    .map((row) => {
      const [timestamp, , , , msg, proto, src, , dst, dstPort] = row;
      const isAttack = !String(msg).includes('Normal');
      return `<tr>
        <td>${escapeHtml(timestamp)}</td>
        <td>${escapeHtml(msg)}</td>
        <td><span class="severity-badge ${isAttack ? 'probe' : 'normal'}">${escapeHtml(proto)}</span></td>
        <td>${escapeHtml(src)}</td>
        <td>${escapeHtml(dst)}</td>
        <td>${escapeHtml(dstPort)}</td>
      </tr>`;
    })
    .join('');
}

// ─── Render: Summary Tiles (Detection) ──────────────────────────────
function renderOverview(summary = null, totalVectors = 0) {
  if (!summary) {
    dom.statTotal.textContent = '—';
    dom.statAttacks.textContent = '—';
    dom.statNormal.textContent = '—';
    dom.statConfidence.textContent = '—';
    return;
  }

  const counts = summary.predicted_counts || {};
  const normalCount = counts.Normal || 0;
  const attackCount = totalVectors - normalCount;

  animateValue(dom.statTotal, totalVectors);
  animateValue(dom.statAttacks, attackCount);
  animateValue(dom.statNormal, normalCount);
  animateValue(dom.statConfidence, (summary.mean_confidence || 0) * 100, { decimals: 1, suffix: '%' });
}

// ─── Render: Detection Tiles (per-class) ────────────────────────────
function renderDetectionTiles(summary = null) {
  if (!summary) {
    dom.detectionTiles.innerHTML = '';
    return;
  }

  const counts = summary.predicted_counts || {};
  const tiles = Object.entries(counts).map(([label, count]) => {
    const sev = severityOf(label);
    return `<article class="stat-tile" style="border-left: 3px solid ${sev.color};">
      <span class="stat-label">${escapeHtml(label)}</span>
      <span class="stat-value" style="color: ${sev.color}; font-size: 1.3rem;">${count}</span>
    </article>`;
  });

  const confTile = `<article class="stat-tile" style="border-left: 3px solid #fbbf24;">
    <span class="stat-label">Mean Confidence</span>
    <span class="stat-value" style="color: #fbbf24; font-size: 1.3rem;">${(summary.mean_confidence || 0).toFixed(4)}</span>
  </article>`;

  const maxConfTile = `<article class="stat-tile" style="border-left: 3px solid #a78bfa;">
    <span class="stat-label">Max Confidence</span>
    <span class="stat-value" style="color: #a78bfa; font-size: 1.3rem;">${(summary.max_confidence || 0).toFixed(4)}</span>
  </article>`;

  dom.detectionTiles.innerHTML = [...tiles, confTile, maxConfTile].join('');
}

// ─── Render: Predictions Table ──────────────────────────────────────
function renderPredictions(items = []) {
  if (!items.length) {
    dom.predictionBody.innerHTML = '<tr class="empty-row"><td colspan="4">No predictions yet</td></tr>';
    return;
  }

  dom.predictionBody.innerHTML = items
    .map((item) => {
      const sev = severityOf(item.predicted_label);
      const conf = Number(item.confidence || 0);
      const conf2 = Number(item.top_2_confidence || 0);
      return `<tr>
        <td>
          <span class="severity-badge ${sev.css}">
            <span class="severity-dot"></span>
            ${escapeHtml(item.predicted_label)}
          </span>
        </td>
        <td>
          <div class="confidence-cell">
            <div class="confidence-bar">
              <div class="confidence-bar-fill" style="width: ${conf * 100}%; background: ${sev.color};"></div>
            </div>
            ${conf.toFixed(4)}
          </div>
        </td>
        <td>${escapeHtml(item.top_2_label || '—')}</td>
        <td>${conf2.toFixed(4)}</td>
      </tr>`;
    })
    .join('');
}

// ─── Charts ─────────────────────────────────────────────────────────
function initCharts() {
  if (typeof Chart === 'undefined') return;

  Chart.defaults.color = '#8b99b0';
  Chart.defaults.borderColor = 'rgba(99,128,175,0.1)';
  Chart.defaults.font.family = "'IBM Plex Mono', monospace";
  Chart.defaults.font.size = 11;

  // Donut
  const donutCtx = dom.donutCanvas.getContext('2d');
  state.donutChart = new Chart(donutCtx, {
    type: 'doughnut',
    data: {
      labels: ['Normal', 'DoS', 'Probe', 'R2L', 'U2R'],
      datasets: [{
        data: [0, 0, 0, 0, 0],
        backgroundColor: CHART_COLORS,
        borderColor: '#111827',
        borderWidth: 2,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '62%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { padding: 14, usePointStyle: true, pointStyleWidth: 8 },
        },
      },
    },
  });

  // Line
  const lineCtx = dom.lineCanvas.getContext('2d');
  state.lineChart = new Chart(lineCtx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'Attacks',
          data: [],
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239,68,68,0.08)',
          fill: true,
          tension: 0.35,
          pointRadius: 3,
          pointHoverRadius: 5,
        },
        {
          label: 'Normal',
          data: [],
          borderColor: '#2dd4a8',
          backgroundColor: 'rgba(45,212,168,0.06)',
          fill: true,
          tension: 0.35,
          pointRadius: 3,
          pointHoverRadius: 5,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { grid: { display: false } },
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(99,128,175,0.08)' },
          ticks: { precision: 0 },
        },
      },
      plugins: {
        legend: {
          labels: { usePointStyle: true, pointStyleWidth: 8 },
        },
      },
    },
  });
}

function updateDonutChart(summary) {
  if (!state.donutChart || !summary) return;
  const counts = summary.predicted_counts || {};
  state.donutChart.data.datasets[0].data = [
    counts.Normal || 0,
    counts.DoS || 0,
    counts.Probe || 0,
    counts.R2L || 0,
    counts.U2R || 0,
  ];
  state.donutChart.update('none');
}

function updateLineChart(summary) {
  if (!state.lineChart || !summary) return;
  const counts = summary.predicted_counts || {};
  const normalCount = counts.Normal || 0;
  const attackCount = Object.entries(counts)
    .filter(([k]) => k !== 'Normal')
    .reduce((sum, [, v]) => sum + v, 0);

  const now = new Date();
  const label = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  const chart = state.lineChart;
  chart.data.labels.push(label);
  chart.data.datasets[0].data.push(attackCount);
  chart.data.datasets[1].data.push(normalCount);

  // Keep last 15 points
  if (chart.data.labels.length > 15) {
    chart.data.labels.shift();
    chart.data.datasets[0].data.shift();
    chart.data.datasets[1].data.shift();
  }

  chart.update('none');
}

// ─── Generate Attack Notifications ──────────────────────────────────
function notifyAttacks(summary) {
  if (!summary || !summary.predicted_counts) return;
  const counts = summary.predicted_counts;

  const attackTypes = ['DoS', 'Probe', 'R2L', 'U2R'];
  const sevIcons = { DoS: '⚠️', Probe: '🔍', R2L: '🔓', U2R: '💀' };

  for (const type of attackTypes) {
    if (counts[type] && counts[type] > 0) {
      showToast(`${counts[type]} ${type} attack(s) detected!`, {
        icon: sevIcons[type],
        danger: type === 'U2R' || type === 'R2L',
        duration: type === 'U2R' ? 6000 : 4000,
      });
    }
  }
}

// ─── API Actions ────────────────────────────────────────────────────
async function simulateOnly() {
  setBusy(true);
  dom.simMeta.textContent = 'Generating synthetic Snort alerts…';
  dom.detectMeta.textContent = '';

  try {
    const payload = { ...requestPayload(), output_name: 'website_simulated_alerts.csv' };
    const result = await api('/api/simulate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    state.lastSimulation = result;
    renderAlerts(result.preview_rows);
    dom.simMeta.textContent = `Session ${result.session_id} — CSV: ${result.output_csv}`;
    dom.detectLatestBtn.disabled = false;
    showToast(`Simulation complete: ${result.total_events} events`, { icon: '⚡' });
  } catch (err) {
    dom.simMeta.textContent = `Simulation failed: ${err.message}`;
    showToast(`Simulation error: ${err.message}`, { icon: '❌', danger: true });
  } finally {
    setBusy(false);
  }
}

async function detectLatest() {
  if (!state.lastSimulation) return;
  setBusy(true);
  dom.detectMeta.textContent = 'Running FT-Transformer detection…';

  try {
    const payload = {
      alert_csv_path: state.lastSimulation.output_csv,
      window_seconds: numberVal(dom.windowSeconds, 2),
      benign_ratio: numberVal(dom.benignRatio, 0.35),
      total_events: numberVal(dom.totalEvents, 120),
    };
    const result = await api('/api/detect', { method: 'POST', body: JSON.stringify(payload) });
    handleDetectionResult(result);
  } catch (err) {
    dom.detectMeta.textContent = `Detection failed: ${err.message}`;
    showToast(`Detection error: ${err.message}`, { icon: '❌', danger: true });
  } finally {
    setBusy(false);
  }
}

async function simulateAndDetect() {
  setBusy(true);
  dom.simMeta.textContent = 'Simulating and detecting in one flow…';

  try {
    const result = await api('/api/detect', {
      method: 'POST',
      body: JSON.stringify(requestPayload()),
    });
    handleDetectionResult(result);
  } catch (err) {
    dom.detectMeta.textContent = `Failed: ${err.message}`;
    showToast(`Error: ${err.message}`, { icon: '❌', danger: true });
  } finally {
    setBusy(false);
  }
}

function handleDetectionResult(result) {
  renderOverview(result.summary, result.total_vectors);
  renderDetectionTiles(result.summary);
  renderPredictions(result.sample_predictions);
  updateDonutChart(result.summary);
  updateLineChart(result.summary);
  notifyAttacks(result.summary);

  dom.detectMeta.textContent = `Session ${result.session_id} — ${result.total_vectors} vectors — ${result.predictions_csv}`;
  showToast(`Detection complete: ${result.total_vectors} vectors analyzed`, { icon: '🛡️' });

  state.sessionHistory.push({
    id: result.session_id,
    time: new Date().toLocaleTimeString(),
    total: result.total_vectors,
    summary: result.summary,
  });
}

// ─── Sidebar Nav ────────────────────────────────────────────────────
document.querySelectorAll('.nav-item').forEach((item) => {
  item.addEventListener('click', (e) => {
    document.querySelectorAll('.nav-item').forEach((n) => n.classList.remove('active'));
    item.classList.add('active');
  });
});

// ─── Event Listeners ────────────────────────────────────────────────
dom.simulateBtn.addEventListener('click', simulateOnly);
dom.detectLatestBtn.addEventListener('click', detectLatest);
dom.simulateDetectBtn.addEventListener('click', simulateAndDetect);

// ─── Init ───────────────────────────────────────────────────────────
renderAlerts([]);
renderPredictions([]);

// Wait for Chart.js to load
function tryInitCharts() {
  if (typeof Chart !== 'undefined') {
    initCharts();
  } else {
    setTimeout(tryInitCharts, 100);
  }
}
tryInitCharts();
