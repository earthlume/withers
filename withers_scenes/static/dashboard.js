function fmtUptime(s) {
  const d = Math.floor(s/86400), h = Math.floor((s%86400)/3600);
  const m = Math.floor((s%3600)/60), sec = Math.floor(s%60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m ${sec}s`;
  return `${m}m ${sec}s`;
}
function fmtTimeAgo(ts) {
  const dt = Date.now()/1000 - ts;
  if (dt < 60) return `${Math.floor(dt)}s ago`;
  if (dt < 3600) return `${Math.floor(dt/60)}m ago`;
  return `${Math.floor(dt/3600)}h${Math.floor((dt%3600)/60)}m ago`;
}
function rgb2hex(r,g,b) {
  return '#' + [r,g,b].map(x => x.toString(16).padStart(2,'0')).join('');
}

const prev = document.getElementById('preview');
for (let i = 0; i < 64; i++) {
  const d = document.createElement('div');
  d.className = 'px'; prev.appendChild(d);
}
const pxs = prev.querySelectorAll('.px');

function drawChart(canvas, series, palette) {
  const ctx = canvas.getContext('2d');
  const W = canvas.width = canvas.clientWidth * devicePixelRatio;
  const H = canvas.height = 140 * devicePixelRatio;
  ctx.scale(devicePixelRatio, devicePixelRatio);
  const w = canvas.clientWidth, h = 140;
  ctx.clearRect(0, 0, w, h);
  if (!series || series.length === 0 || series[0].values.length === 0) {
    ctx.fillStyle = '#5a4a2a'; ctx.font = 'italic 12px "Cormorant Garamond", serif';
    ctx.fillText('The ledger awaits its first entry…', 10, 70);
    return;
  }
  const allVals = series.flatMap(s => s.values);
  const min = Math.min(...allVals), max = Math.max(...allVals);
  const range = max - min || 1;
  const n = series[0].values.length;
  series.forEach((s, i) => {
    ctx.strokeStyle = palette[i]; ctx.lineWidth = 1.5;
    ctx.beginPath();
    s.values.forEach((v, j) => {
      const x = (j / (n - 1)) * (w - 10) + 5;
      const y = h - 10 - ((v - min) / range) * (h - 20);
      if (j === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.fillStyle = palette[i];
    ctx.font = '10px ui-monospace, monospace';
    ctx.fillText(`${s.name}: ${s.values[s.values.length-1].toFixed(1)}`, 6, 14 + i*12);
  });
}

async function refreshStatus() {
  try {
    const r = await fetch('/api/status'); const d = await r.json();
    document.getElementById('scene').textContent = d.scene || '—';
    const stEl = document.getElementById('state');
    stEl.textContent = d.state || '—';
    stEl.className = 'state-tag state-' + (d.state || '');
    document.getElementById('uptime').textContent = fmtUptime(d.uptime_s);
    document.getElementById('disturbance').textContent = d.disturbance_active ? 'ACTIVE' : '—';
    document.getElementById('disturbance').className = d.disturbance_active ? 'v warn' : 'v';
    document.getElementById('storm').textContent = d.pressure_drop_active ? 'GATHERING' : '—';
    document.getElementById('storm').className = d.pressure_drop_active ? 'v warn' : 'v';
    document.getElementById('temp').textContent = d.temperature.toFixed(1) + ' °C';
    document.getElementById('hum').textContent  = d.humidity.toFixed(1) + ' %';
    document.getElementById('pres').textContent = d.pressure.toFixed(1) + ' hPa';
    document.getElementById('amag').textContent = d.accel_magnitude.toFixed(2) + ' g';
    document.getElementById('gz').textContent   = d.gyro_z.toFixed(1) + ' °/s';
    document.getElementById('tilt').textContent = `(${d.tilt[0].toFixed(2)}, ${d.tilt[1].toFixed(2)})`;
    document.getElementById('mag').textContent  = d.mag.map(v => v.toFixed(1)).join(' / ');
    document.getElementById('bready').textContent = d.baseline_ready ? 'aye' : 'not yet';
    if (d.baseline) {
      document.getElementById('bage').textContent = fmtTimeAgo(d.baseline.saved_at);
      document.getElementById('bmeta').textContent =
        `n=${d.baseline.n_samples}  σ=[${d.baseline.std.map(v=>v.toFixed(1)).join(', ')}]`;
    }
  } catch (e) {}
}

async function refreshPreview() {
  try {
    const r = await fetch('/api/preview'); const d = await r.json();
    d.frame.forEach((px, i) => { pxs[i].style.background = rgb2hex(px[0], px[1], px[2]); });
  } catch (e) {}
}

async function refreshCharts() {
  try {
    const r = await fetch('/api/sensors?seconds=3600'); const d = await r.json();
    const s = d.samples;
    if (s.length > 0) {
      drawChart(document.getElementById('chart1'), [
        { name: 'temp °C', values: s.map(r => r.temperature) },
        { name: 'hum %',   values: s.map(r => r.humidity) },
      ], ['#e8bc4d', '#4a9e8a']);
      drawChart(document.getElementById('chart2'), [
        { name: 'hPa',     values: s.map(r => r.pressure) },
      ], ['#d88a2a']);
    }
  } catch (e) {}
}

async function refreshHistory() {
  try {
    const r = await fetch('/api/scenes?limit=25'); const d = await r.json();
    const el = document.getElementById('history');
    el.innerHTML = d.history.map(h => `
      <div class="row">
        <span class="scene">${h.scene}</span>
        <span><span class="state-tag state-${h.state}">${h.state}</span></span>
        <span class="time">${fmtTimeAgo(h.ts)}</span>
      </div>`).join('');
  } catch (e) {}
}

refreshStatus(); refreshPreview(); refreshCharts(); refreshHistory();
setInterval(refreshStatus, 1500);
setInterval(refreshPreview, 500);
setInterval(refreshCharts, 10000);
setInterval(refreshHistory, 5000);
