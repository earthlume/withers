"""SQLite persistence for sensor samples, scene history, events.

Single writer thread (WriterThread) drains a queue. Scenes/main push events
via module-level helper functions. Queries for the dashboard read directly
(SQLite handles concurrent read while a writer is active).
"""
import queue, sqlite3, threading, time
from pathlib import Path

DB_PATH = Path.home() / "Withers" / "withers.db"
WRITE_Q = queue.Queue(maxsize=10000)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sensor_samples (
    ts REAL PRIMARY KEY,
    temperature REAL, humidity REAL, pressure REAL,
    accel_mag REAL, gyro_z REAL,
    mag_x REAL, mag_y REAL, mag_z REAL
);
CREATE INDEX IF NOT EXISTS idx_sensor_ts ON sensor_samples(ts);

CREATE TABLE IF NOT EXISTS scene_history (
    ts REAL PRIMARY KEY,
    scene TEXT NOT NULL,
    state TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scene_ts ON scene_history(ts);

CREATE TABLE IF NOT EXISTS events (
    ts REAL PRIMARY KEY,
    kind TEXT NOT NULL,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
"""

# Retention thresholds
SENSOR_RETENTION_DAYS = 7
SCENE_RETENTION_COUNT = 500
EVENT_RETENTION_DAYS  = 30


class WriterThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="db-writer")
        self._stop = threading.Event()
        self._last_cleanup = 0.0

    def stop(self):
        self._stop.set()

    def run(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        conn.executescript(SCHEMA)
        conn.commit()
        while not self._stop.is_set():
            try:
                item = WRITE_Q.get(timeout=0.5)
            except queue.Empty:
                item = None
            if item is not None:
                kind, payload = item
                try:
                    if kind == 'sensor':
                        conn.execute(
                            "INSERT OR REPLACE INTO sensor_samples VALUES (?,?,?,?,?,?,?,?,?)",
                            payload,
                        )
                    elif kind == 'scene':
                        conn.execute(
                            "INSERT OR REPLACE INTO scene_history VALUES (?,?,?)",
                            payload,
                        )
                    elif kind == 'event':
                        conn.execute(
                            "INSERT OR REPLACE INTO events VALUES (?,?,?)",
                            payload,
                        )
                    conn.commit()
                except Exception:
                    pass  # never crash writer on bad row
            # Periodic retention cleanup
            now = time.time()
            if now - self._last_cleanup > 3600:  # once per hour
                try:
                    conn.execute(
                        "DELETE FROM sensor_samples WHERE ts < ?",
                        (now - SENSOR_RETENTION_DAYS * 86400,),
                    )
                    conn.execute(
                        "DELETE FROM scene_history WHERE ts NOT IN "
                        "(SELECT ts FROM scene_history ORDER BY ts DESC LIMIT ?)",
                        (SCENE_RETENTION_COUNT,),
                    )
                    conn.execute(
                        "DELETE FROM events WHERE ts < ?",
                        (now - EVENT_RETENTION_DAYS * 86400,),
                    )
                    conn.commit()
                    self._last_cleanup = now
                except Exception:
                    pass
        conn.close()


def record_sensor(state):
    """Call at 1 Hz. Reads SensorState and enqueues a row."""
    row = (
        time.time(),
        state.temperature, state.humidity, state.pressure,
        state.accel_magnitude, state.gyro_z,
        state.mag[0], state.mag[1], state.mag[2],
    )
    try: WRITE_Q.put_nowait(('sensor', row))
    except queue.Full: pass


def record_scene(name, state_name):
    row = (time.time(), name, state_name)
    try: WRITE_Q.put_nowait(('scene', row))
    except queue.Full: pass


def record_event(kind, detail=""):
    row = (time.time(), kind, detail)
    try: WRITE_Q.put_nowait(('event', row))
    except queue.Full: pass


# --- Query helpers (for dashboard) --------------------------------
def _connect():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def query_sensor_range(seconds_back=3600, downsample_to=200):
    """Return up to downsample_to rows from the last `seconds_back` seconds."""
    if not DB_PATH.exists(): return []
    conn = _connect()
    cutoff = time.time() - seconds_back
    cur = conn.execute(
        "SELECT COUNT(*) FROM sensor_samples WHERE ts >= ?", (cutoff,)
    )
    n = cur.fetchone()[0]
    if n == 0:
        conn.close(); return []
    step = max(1, n // downsample_to)
    rows = conn.execute(
        "SELECT * FROM sensor_samples WHERE ts >= ? AND ROWID % ? = 0 ORDER BY ts ASC",
        (cutoff, step),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_scenes(limit=20):
    if not DB_PATH.exists(): return []
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM scene_history ORDER BY ts DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_events(limit=50):
    if not DB_PATH.exists(): return []
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM events ORDER BY ts DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
