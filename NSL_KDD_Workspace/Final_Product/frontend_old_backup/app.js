const SEVERITY_MAP = {
  Normal: { css: 'normal', color: '#2dd4a8' },
  DoS: { css: 'dos', color: '#f59e0b' },
  Probe: { css: 'probe', color: '#3b82f6' },
  R2L: { css: 'r2l', color: '#f97316' },
  U2R: { css: 'u2r', color: '#ef4444' },
};

const CHART_COLORS = ['#2dd4a8', '#f59e0b', '#3b82f6', '#f97316', '#ef4444'];

const state = {
  lastSimulation: null,
  donutChart: null,
  lineChart: null,
  featureCompareChart: null,
  confidenceDistChart: null,
};

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
  featurePreviewBody: document.getElementById('featurePreviewBody'),
  abnormalFlagsBody: document.getElementById('abnormalFlagsBody'),
  diagnosticTiles: document.getElementById('diagnosticTiles'),
  toastContainer: document.getElementById('toastContainer'),
  statTotal: document.getElementById('statTotal'),
  statAttacks: document.getElementById('statAttacks'),
  statNormal: document.getElementById('statNormal'),
  statConfidence: document.getElementById('statConfidence'),
  donutCanvas: document.getElementById('donutChart'),
  lineCanvas: document.getElementById('lineChart'),
  featureCompareCanvas: document.getElementById('featureCompareChart'),
  confidenceDistCanvas: document.getElementById('confidenceDistChart'),
};

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
  if (!response.ok) throw new Error(data.detail || `Request failed: ${response.status}`);
  return data;
}

function updateClock() {
  dom.headerClock.textContent = new Date().toLocaleTimeString('en-GB', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}
setInterval(updateClock, 1000);
updateClock();

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

function setBusy(isBusy) {
  dom.simulateBtn.disabled = isBusy;
  dom.simulateDetectBtn.disabled = isBusy;
  dom.detectLatestBtn.disabled = isBusy || !state.lastSimulation;
  dom.simulateDetectBtn.innerHTML = isBusy
    ? '<span class="spinner"></span> Processing...'
    : '<span class="btn-icon">🚀</span> Simulate + Detect';
}

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

function renderAlerts(previewRows = []) {
  if (!previewRows.length) {
    dom.alertPreviewBody.innerHTML = '<tr class="empty-row"><td colspan="6">No alerts - run a simulation first</td></tr>';
    return;
  }

  dom.alertPreviewBody.innerHTML = previewRows.map((row) => {
    const [timestamp, , , , msg, proto, src, , dst, dstPort] = row;
    const attack = !String(msg).includes('Normal');
    return `<tr>
      <td>${escapeHtml(timestamp)}</td>
      <td>${escapeHtml(msg)}</td>
      <td><span class="severity-badge ${attack ? 'probe' : 'normal'}">${escapeHtml(proto)}</span></td>
      <td>${escapeHtml(src)}</td>
      <td>${escapeHtml(dst)}</td>
      <td>${escapeHtml(dstPort)}</td>
    </tr>`;
  }).join('');
}

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
  dom.statTotal.textContent = String(totalVectors);
  dom.statAttacks.textContent = String(totalVectors - normalCount);
  dom.statNormal.textContent = String(normalCount);
  dom.statConfidence.textContent = `${((summary.mean_confidence || 0) * 100).toFixed(1)}%`;
}

function renderDetectionTiles(summary = null) {
  if (!summary) {
    dom.detectionTiles.innerHTML = '';
    return;
  }

  const counts = summary.predicted_counts || {};
  const tiles = Object.entries(counts).map(([label, count]) => {
    const sev = SEVERITY_MAP[label] || SEVERITY_MAP.Normal;
    return `<article class="stat-tile" style="border-left: 3px solid ${sev.color};">
      <span class="stat-label">${escapeHtml(label)}</span>
      <span class="stat-value" style="color:${sev.color}; font-size:1.2rem;">${count}</span>
    </article>`;
  });

  tiles.push(`<article class="stat-tile"><span class="stat-label">Stage-1 Normal Gate</span><span class="stat-value" style="font-size:1.2rem;">${((summary.stage1_normal_gate_rate || 0) * 100).toFixed(1)}%</span></article>`);
  tiles.push(`<article class="stat-tile"><span class="stat-label">Slow Attack Ratio</span><span class="stat-value" style="font-size:1.2rem;">${((summary.slow_attack_ratio || 0) * 100).toFixed(1)}%</span></article>`);

  dom.detectionTiles.innerHTML = tiles.join('');
}

function renderPredictions(items = []) {
  if (!items.length) {
    dom.predictionBody.innerHTML = '<tr class="empty-row"><td colspan="6">No predictions yet</td></tr>';
    return;
  }

  dom.predictionBody.innerHTML = items.map((item) => {
    const sev = SEVERITY_MAP[item.predicted_label] || SEVERITY_MAP.Normal;
    const conf = Number(item.confidence || 0);
    return `<tr>
      <td><span class="severity-badge ${sev.css}"><span class="severity-dot"></span>${escapeHtml(item.predicted_label)}</span></td>
      <td><div class="confidence-cell"><div class="confidence-bar"><div class="confidence-bar-fill" style="width:${conf * 100}%; background:${sev.color};"></div></div>${conf.toFixed(4)}</div></td>
      <td>${Number(item.stage1_mse || 0).toFixed(6)}</td>
      <td>${escapeHtml(item.traffic_pattern_label || 'StandardTrafficPattern')}</td>
      <td>${escapeHtml(item.top_2_label || '—')}</td>
      <td>${Number(item.top_2_confidence || 0).toFixed(4)}</td>
    </tr>`;
  }).join('');
}

function renderFeatureTable(inputProfile = null, datasetProfile = null) {
  if (!inputProfile || !datasetProfile) {
    dom.featurePreviewBody.innerHTML = '<tr class="empty-row"><td colspan="5">No feature profile yet</td></tr>';
    return;
  }

  const means = inputProfile.selected_feature_means || {};
  const stds = inputProfile.selected_feature_std || {};
  const dsMeans = datasetProfile.feature_means || {};
  const dsP95 = datasetProfile.feature_p95 || {};

  const features = Object.keys(means);
  dom.featurePreviewBody.innerHTML = features.length
    ? features.map((name) => `<tr>
      <td>${escapeHtml(name)}</td>
      <td>${Number(means[name] || 0).toFixed(6)}</td>
      <td>${Number(stds[name] || 0).toFixed(6)}</td>
      <td>${Number(dsMeans[name] || 0).toFixed(6)}</td>
      <td>${Number(dsP95[name] || 0).toFixed(6)}</td>
    </tr>`).join('')
    : '<tr class="empty-row"><td colspan="5">No feature profile yet</td></tr>';
}

function renderDiagnostics(summary = null) {
  if (!summary) {
    dom.diagnosticTiles.innerHTML = '';
    dom.abnormalFlagsBody.innerHTML = '<tr class="empty-row"><td>No diagnostics yet</td></tr>';
    return;
  }

  dom.diagnosticTiles.innerHTML = [
    `<article class="stat-tile"><span class="stat-label">Dominant Label</span><span class="stat-value" style="font-size:1.2rem;">${escapeHtml(summary.dominant_label || 'NA')}</span><span class="stat-sub">${((summary.dominant_label_share || 0) * 100).toFixed(1)}%</span></article>`,
    `<article class="stat-tile"><span class="stat-label">High Confidence Share</span><span class="stat-value" style="font-size:1.2rem;">${((summary.high_confidence_share || 0) * 100).toFixed(1)}%</span><span class="stat-sub">>=95%</span></article>`,
    `<article class="stat-tile"><span class="stat-label">Autoencoder Threshold</span><span class="stat-value" style="font-size:1.2rem;">${Number(summary.autoencoder_threshold || 0).toFixed(6)}</span></article>`,
    `<article class="stat-tile"><span class="stat-label">Slow Attack Count</span><span class="stat-value" style="font-size:1.2rem;">${summary.slow_attack_count || 0}</span></article>`,
    `<article class="stat-tile"><span class="stat-label">Effective Attack Ratio</span><span class="stat-value" style="font-size:1.2rem;">${((summary.effective_attack_ratio || 0) * 100).toFixed(1)}%</span></article>`,
    `<article class="stat-tile"><span class="stat-label">Risk Override</span><span class="stat-value" style="font-size:1.2rem;">${summary.risk_override_count || 0}</span><span class="stat-sub">${summary.risk_override_applied ? 'active' : 'inactive'}</span></article>`,
  ].join('');

  const flags = summary.abnormal_flags || [];
  dom.abnormalFlagsBody.innerHTML = flags.length
    ? flags.map((flag) => `<tr><td><span class="severity-badge u2r">⚠</span> ${escapeHtml(flag)}</td></tr>`).join('')
    : '<tr><td>No abnormal output flag detected.</td></tr>';
}

function initCharts() {
  if (typeof Chart === 'undefined') return;

  state.donutChart = new Chart(dom.donutCanvas.getContext('2d'), {
    type: 'doughnut',
    data: {
      labels: ['Normal', 'DoS', 'Probe', 'R2L', 'U2R'],
      datasets: [{ data: [0, 0, 0, 0, 0], backgroundColor: CHART_COLORS, borderColor: '#111827', borderWidth: 2 }],
    },
    options: { responsive: true, maintainAspectRatio: true, cutout: '62%' },
  });

  state.lineChart = new Chart(dom.lineCanvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        { label: 'Attacks', data: [], borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.08)', fill: true, tension: 0.35 },
        { label: 'Normal', data: [], borderColor: '#2dd4a8', backgroundColor: 'rgba(45,212,168,0.06)', fill: true, tension: 0.35 },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false },
  });

  state.featureCompareChart = new Chart(dom.featureCompareCanvas.getContext('2d'), {
    type: 'bar',
    data: { labels: [], datasets: [{ label: 'Input Mean', data: [], backgroundColor: 'rgba(96,165,250,0.65)' }, { label: 'Dataset Mean', data: [], backgroundColor: 'rgba(45,212,168,0.65)' }] },
    options: { responsive: true, maintainAspectRatio: false },
  });

  state.confidenceDistChart = new Chart(dom.confidenceDistCanvas.getContext('2d'), {
    type: 'radar',
    data: {
      labels: ['Mean Conf', 'High Conf', 'Dominant Share', 'Stage1 Normal', 'Slow Ratio'],
      datasets: [{ label: 'Runtime', data: [0, 0, 0, 0, 0], borderColor: '#fbbf24', backgroundColor: 'rgba(251,191,36,0.16)' }],
    },
    options: { responsive: true, maintainAspectRatio: false, scales: { r: { beginAtZero: true, max: 1 } } },
  });
}

function updateDonutChart(summary) {
  if (!state.donutChart || !summary) return;
  const counts = summary.predicted_counts || {};
  state.donutChart.data.datasets[0].data = [counts.Normal || 0, counts.DoS || 0, counts.Probe || 0, counts.R2L || 0, counts.U2R || 0];
  state.donutChart.update('none');
}

function updateLineChart(summary) {
  if (!state.lineChart || !summary) return;
  const counts = summary.predicted_counts || {};
  const normalCount = counts.Normal || 0;
  const attackCount = Object.entries(counts).filter(([k]) => k !== 'Normal').reduce((sum, [, v]) => sum + v, 0);
  const label = new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  state.lineChart.data.labels.push(label);
  state.lineChart.data.datasets[0].data.push(attackCount);
  state.lineChart.data.datasets[1].data.push(normalCount);

  if (state.lineChart.data.labels.length > 15) {
    state.lineChart.data.labels.shift();
    state.lineChart.data.datasets[0].data.shift();
    state.lineChart.data.datasets[1].data.shift();
  }
  state.lineChart.update('none');
}

function updateFeatureCompareChart(inputProfile, datasetProfile) {
  if (!state.featureCompareChart || !inputProfile || !datasetProfile) return;
  const inputMeans = inputProfile.selected_feature_means || {};
  const dsMeans = datasetProfile.feature_means || {};
  const labels = Object.keys(inputMeans).slice(0, 10);
  state.featureCompareChart.data.labels = labels;
  state.featureCompareChart.data.datasets[0].data = labels.map((k) => Number(inputMeans[k] || 0));
  state.featureCompareChart.data.datasets[1].data = labels.map((k) => Number(dsMeans[k] || 0));
  state.featureCompareChart.update('none');
}

function updateConfidenceDistChart(summary) {
  if (!state.confidenceDistChart || !summary) return;
  state.confidenceDistChart.data.datasets[0].data = [
    Number(summary.mean_confidence || 0),
    Number(summary.high_confidence_share || 0),
    Number(summary.dominant_label_share || 0),
    Number(summary.stage1_normal_gate_rate || 0),
    Number(summary.slow_attack_ratio || 0),
  ];
  state.confidenceDistChart.update('none');
}

function notifyAttacks(summary) {
  if (!summary || !summary.predicted_counts) return;
  const counts = summary.predicted_counts;
  const icons = { DoS: '⚠️', Probe: '🔍', R2L: '🔓', U2R: '💀' };
  ['DoS', 'Probe', 'R2L', 'U2R'].forEach((type) => {
    if (counts[type] && counts[type] > 0) {
      showToast(`${counts[type]} ${type} attack(s) detected`, { icon: icons[type], danger: type === 'R2L' || type === 'U2R' });
    }
  });
  if (summary.slow_attack_count > 0) {
    showToast(`Slow attack candidates: ${summary.slow_attack_count}`, { icon: '🐢', danger: true, duration: 5500 });
  }
  if (summary.risk_override_applied) {
    showToast(`Risk override promoted ${summary.risk_override_count} slow-scan vector(s)`, { icon: '🧯', danger: true, duration: 6000 });
  }
}

async function simulateOnly() {
  setBusy(true);
  dom.simMeta.textContent = 'Generating synthetic Snort alerts...';
  dom.detectMeta.textContent = '';

  try {
    const payload = { ...requestPayload(), output_name: 'website_simulated_alerts.csv' };
    const result = await api('/api/simulate', { method: 'POST', body: JSON.stringify(payload) });
    state.lastSimulation = result;
    renderAlerts(result.preview_rows);
    dom.simMeta.textContent = `Session ${result.session_id} - CSV: ${result.output_csv}`;
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
  dom.detectMeta.textContent = 'Running two-stage detection...';

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
  dom.simMeta.textContent = 'Simulating and detecting...';

  try {
    const result = await api('/api/detect', { method: 'POST', body: JSON.stringify(requestPayload()) });
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
  renderPredictions(result.sample_predictions || []);
  renderFeatureTable(result.input_profile, result.dataset_profile);
  renderDiagnostics(result.summary);

  updateDonutChart(result.summary);
  updateLineChart(result.summary);
  updateFeatureCompareChart(result.input_profile, result.dataset_profile);
  updateConfidenceDistChart(result.summary);

  notifyAttacks(result.summary);
  dom.detectMeta.textContent = `Session ${result.session_id} - ${result.total_vectors} vectors - ${result.predictions_csv}`;
  showToast(`Detection complete: ${result.total_vectors} vectors analyzed`, { icon: '🛡️' });
}

document.querySelectorAll('.nav-item').forEach((item) => {
  item.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach((n) => n.classList.remove('active'));
    item.classList.add('active');
  });
});

dom.simulateBtn.addEventListener('click', simulateOnly);
dom.detectLatestBtn.addEventListener('click', detectLatest);
dom.simulateDetectBtn.addEventListener('click', simulateAndDetect);

renderAlerts([]);
renderPredictions([]);
renderFeatureTable(null, null);
renderDiagnostics(null);

function bootCharts() {
  if (typeof Chart !== 'undefined') initCharts();
  else setTimeout(bootCharts, 120);
}
bootCharts();
