"""FastAPI dashboard. Embedded in withers-scenes process via uvicorn thread."""
import json, threading, time
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from . import storage
from .sensors import BASELINE_PATH

_pkg_dir = Path(__file__).parent
_templates = Jinja2Templates(directory=str(_pkg_dir / "templates"))


def make_app(shared):
    app = FastAPI(title="Withers", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=str(_pkg_dir / "static")), name="static")

    @app.get("/api/status")
    def status():
        s = shared['state']; sc = shared['sched']
        base = None
        if BASELINE_PATH.exists():
            try: base = json.loads(BASELINE_PATH.read_text())
            except Exception: pass
        return {
            'uptime_s': time.time() - shared['start_ts'],
            'scene': sc.last_scene, 'state': sc.state,
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
    def scenes(limit: int = 25):
        return {'history': storage.query_scenes(limit=limit)}

    @app.get("/api/events")
    def events(limit: int = 50):
        return {'events': storage.query_events(limit=limit)}

    @app.get("/api/preview")
    def preview():
        return {'frame': shared['pipe'].last_frame}

    @app.get("/", response_class=HTMLResponse)
    def root(request: Request):
        return _templates.TemplateResponse(request, "index.html")

    @app.get("/about", response_class=HTMLResponse)
    def about(request: Request):
        return _templates.TemplateResponse(request, "about.html")

    return app


def serve(app, host='0.0.0.0', port=8080):
    config = uvicorn.Config(app, host=host, port=port, log_level='warning', access_log=False)
    server = uvicorn.Server(config)
    server.run()


def start_web_thread(shared):
    app = make_app(shared)
    t = threading.Thread(target=serve, args=(app,), daemon=True, name="web")
    t.start()
    return t
