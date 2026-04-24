"""FastAPI dashboard. Reads sensor state + SQLite history.

Embedded in the main withers-scenes process via uvicorn in a thread.
"""
import json, threading, time
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from . import storage
from .sensors import BASELINE_PATH


def make_app(shared):
    """shared is a dict with live references: {'state': SensorState, 'pipe': Pipeline,
    'sched': Scheduler, 'start_ts': float}"""
    app = FastAPI(title="Withers", docs_url=None, redoc_url=None)

    @app.get("/api/status")
    def status():
        s = shared['state']
        sc = shared['sched']
        base = None
        if BASELINE_PATH.exists():
            try:
                base = json.loads(BASELINE_PATH.read_text())
            except Exception:
                pass
        return {
            'uptime_s': time.time() - shared['start_ts'],
            'scene': sc.last_scene,
            'state': sc.state,
            'temperature': round(s.temperature, 2),
            'humidity': round(s.humidity, 2),
            'pressure': round(s.pressure, 2),
            'accel_magnitude': round(s.accel_magnitude, 3),
            'gyro_z': round(s.gyro_z, 2),
            'mag': [round(v, 2) for v in s.mag],
            'tilt': list(s.tilt()),
            'baseline_ready': s.baseline_ready,
            'baseline': base,
            'disturbance_active': s.disturbance_active,
            'pressure_drop_active': s.pressure_drop_active,
        }

    @app.get("/api/sensors")
    def sensors(seconds: int = 3600):
        return {'samples': storage.query_sensor_range(seconds_back=seconds)}

    @app.get("/api/scenes")
    def scenes(limit: int = 20):
        return {'history': storage.query_scenes(limit=limit)}

    @app.get("/api/events")
    def events(limit: int = 50):
        return {'events': storage.query_events(limit=limit)}

    @app.get("/api/preview")
    def preview():
        """Live LED matrix — last rendered frame as 64 RGB tuples."""
        return {'frame': shared['pipe'].last_frame}

    @app.get("/", response_class=HTMLResponse)
    def root():
        return INDEX_HTML

    return app


def serve(app, host='0.0.0.0', port=8080):
    """Run uvicorn. Blocking — call from a thread."""
    config = uvicorn.Config(app, host=host, port=port, log_level='warning', access_log=False)
    server = uvicorn.Server(config)
    server.run()


def start_web_thread(shared):
    app = make_app(shared)
    t = threading.Thread(target=serve, args=(app,), daemon=True, name="web")
    t.start()
    return t


# --- HTML page ----------------------------------------------------
INDEX_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Withers</title>
<style>
:root {
  --bg: #0a0614; --fg: #d9c99a; --dim: #5a4a2a; --accent: #e8bc4d;
  --panel: #14102a; --border: #2a2048; --warm: #d88a2a; --cool: #4a9e8a;
  --crit: #d94030;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--fg); font: 13px/1.4 ui-monospace, "SF Mono", Menlo, monospace; padding: 14px; }
h1 { font-size: 18px; color: var(--accent); letter-spacing: 2px; margin-bottom: 14px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
.panel { background: var(--panel); border: 1px solid var(--border); padding: 12px; border-radius: 4px; }
.panel h2 { font-size: 11px; color: var(--accent); letter-spacing: 1.5px; margin-bottom: 10px; text-transform: uppercase; }
.kv { display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px dashed var(--border); }
.kv:last-child { border: 0; }
.kv .k { color: var(--dim); }
.kv .v { color: var(--fg); font-weight: 600; }
.pulse { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--accent); margin-right: 6px; animation: pulse 1.5s infinite; }
@keyframes pulse { 50% { opacity: 0.3; } }
.preview { display: grid; grid-template-columns: repeat(8, 1fr); gap: 1px; aspect-ratio: 1; background: #000; padding: 2px; }
.preview .px { aspect-ratio: 1; background: #000; }
canvas { width: 100%; height: 120px; display: block; }
.history { max-height: 260px; overflow-y: auto; }
.history .row { padding: 3px 0; display: flex; justify-content: space-between; border-bottom: 1px dashed var(--border); font-size: 12px; }
.history .row .scene { color: var(--accent); }
.history .row .state { color: var(--cool); font-size: 10px; text-transform: uppercase; }
.history .row .time { color: var(--dim); font-size: 11px; }
.state-tag { display: inline-block; padding: 2px 8px; border-radius: 2px; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
.state-contemplative { background: #1a2a3a; color: #88bbff; }
.state-active        { background: #3a2a1a; color: #ffbb88; }
.state-inscribing    { background: #2a1a3a; color: #bb88ff; }
.state-climactic     { background: #3a1a1a; color: #ff8888; }
.state-observing     { background: #1a3a2a; color: #88ffbb; }
.warn { color: var(--crit); font-weight: 700; }
.meta { color: var(--dim); font-size: 10px; margin-top: 8px; }
</style>
</head><body>
<h1><span class="pulse"></span>WITHERS — THE LEDGER OPENS</h1>
<div class="grid">

  <div class="panel">
    <h2>Present</h2>
    <div class="kv"><span class="k">Scene</span><span class="v" id="scene">—</span></div>
    <div class="kv"><span class="k">State</span><span class="v"><span id="state" class="state-tag">—</span></span></div>
    <div class="kv"><span class="k">Uptime</span><span class="v" id="uptime">—</span></div>
    <div class="kv"><span class="k">Disturbance</span><span class="v" id="disturbance">—</span></div>
    <div class="kv"><span class="k">Storm flag</span><span class="v" id="storm">—</span></div>
  </div>

  <div class="panel">
    <h2>Live matrix</h2>
    <div class="preview" id="preview"></div>
    <div class="meta">Updated every 500ms</div>
  </div>

  <div class="panel">
    <h2>Environment</h2>
    <div class="kv"><span class="k">Temperature</span><span class="v" id="temp">—</span></div>
    <div class="kv"><span class="k">Humidity</span><span class="v" id="hum">—</span></div>
    <div class="kv"><span class="k">Pressure</span><span class="v" id="pres">—</span></div>
  </div>

  <div class="panel">
    <h2>IMU</h2>
    <div class="kv"><span class="k">Accel magnitude</span><span class="v" id="amag">—</span></div>
    <div class="kv"><span class="k">Gyro Z</span><span class="v" id="gz">—</span></div>
    <div class="kv"><span class="k">Tilt</span><span class="v" id="tilt">—</span></div>
  </div>

  <div class="panel">
    <h2>Magnetometer</h2>
    <div class="kv"><span class="k">X / Y / Z (µT)</span><span class="v" id="mag">—</span></div>
    <div class="kv"><span class="k">Baseline ready</span><span class="v" id="bready">—</span></div>
    <div class="kv"><span class="k">Baseline age</span><span class="v" id="bage">—</span></div>
    <div class="meta" id="bmeta"></div>
  </div>

  <div class="panel" style="grid-column: span 2;">
    <h2>Temperature &amp; humidity — last hour</h2>
    <canvas id="chart1"></canvas>
  </div>

  <div class="panel" style="grid-column: span 2;">
    <h2>Pressure — last hour</h2>
    <canvas id="chart2"></canvas>
  </div>

  <div class="panel" style="grid-column: span 2;">
    <h2>Scene history</h2>
    <div class="history" id="history"></div>
  </div>

</div>

<script>
function fmtUptime(s) {
  const d = Math.floor(s/86400), h = Math.floor((s%86400)/3600);
  const m = Math.floor((s%3600)/60), sec = Math.floor(s%60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m ${sec}s`;
  return `${m}m ${sec}s`;
}
function fmtTimeAgo(ts) {
  const dt = Date.now()/1000 - ts;
  if (dt < 60) return `${Math.floor(dt)}s`;
  if (dt < 3600) return `${Math.floor(dt/60)}m`;
  return `${Math.floor(dt/3600)}h${Math.floor((dt%3600)/60)}m`;
}
function rgb2hex(r,g,b) {
  return '#' + [r,g,b].map(x => x.toString(16).padStart(2,'0')).join('');
}

// Build matrix preview grid
const prev = document.getElementById('preview');
for (let i = 0; i < 64; i++) {
  const d = document.createElement('div');
  d.className = 'px'; prev.appendChild(d);
}
const pxs = prev.querySelectorAll('.px');

// Canvas chart — minimal, no library
function drawChart(canvas, series, palette) {
  const ctx = canvas.getContext('2d');
  const W = canvas.width = canvas.clientWidth * devicePixelRatio;
  const H = canvas.height = 120 * devicePixelRatio;
  ctx.scale(devicePixelRatio, devicePixelRatio);
  const w = canvas.clientWidth, h = 120;
  ctx.clearRect(0, 0, w, h);
  if (!series || series.length === 0 || series[0].values.length === 0) {
    ctx.fillStyle = '#5a4a2a'; ctx.font = '11px monospace';
    ctx.fillText('(no data yet)', 10, 60);
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
    // label
    ctx.fillStyle = palette[i]; ctx.font = '10px monospace';
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
    document.getElementById('storm').textContent = d.pressure_drop_active ? 'STORM INCOMING' : '—';
    document.getElementById('storm').className = d.pressure_drop_active ? 'v warn' : 'v';
    document.getElementById('temp').textContent = d.temperature.toFixed(1) + ' °C';
    document.getElementById('hum').textContent  = d.humidity.toFixed(1) + ' %';
    document.getElementById('pres').textContent = d.pressure.toFixed(1) + ' hPa';
    document.getElementById('amag').textContent = d.accel_magnitude.toFixed(2) + ' g';
    document.getElementById('gz').textContent   = d.gyro_z.toFixed(1) + ' °/s';
    document.getElementById('tilt').textContent = `(${d.tilt[0].toFixed(2)}, ${d.tilt[1].toFixed(2)})`;
    document.getElementById('mag').textContent  = d.mag.map(v => v.toFixed(1)).join(' / ');
    document.getElementById('bready').textContent = d.baseline_ready ? 'yes' : 'no';
    if (d.baseline) {
      const age_s = Date.now()/1000 - d.baseline.saved_at;
      document.getElementById('bage').textContent = fmtTimeAgo(d.baseline.saved_at) + ' ago';
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
        { name: 'temp °C',  values: s.map(r => r.temperature) },
        { name: 'hum %',    values: s.map(r => r.humidity) },
      ], ['#e8bc4d', '#4a9e8a']);
      drawChart(document.getElementById('chart2'), [
        { name: 'hPa',      values: s.map(r => r.pressure) },
      ], ['#d88a2a']);
    }
  } catch (e) {}
}

async function refreshHistory() {
  try {
    const r = await fetch('/api/scenes?limit=20'); const d = await r.json();
    const el = document.getElementById('history');
    el.innerHTML = d.history.map(h => `
      <div class="row">
        <span class="scene">${h.scene}</span>
        <span><span class="state-tag state-${h.state}">${h.state}</span></span>
        <span class="time">${fmtTimeAgo(h.ts)} ago</span>
      </div>`).join('');
  } catch (e) {}
}

refreshStatus(); refreshPreview(); refreshCharts(); refreshHistory();
setInterval(refreshStatus, 1500);
setInterval(refreshPreview, 500);
setInterval(refreshCharts, 10000);
setInterval(refreshHistory, 5000);
</script>
</body></html>
"""
