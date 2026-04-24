"""Sensor polling, calibration, derived signals.

Background thread samples at 10 Hz. Scenes read from SensorState snapshots.
Thread-safety: single writer (SensorThread), multiple readers (scenes) —
Python GIL makes primitive attribute reads atomic; lists/dicts are only
ever replaced, never mutated in place.
"""
import json, math, os, threading, time
from collections import deque
from pathlib import Path
from sense_hat import SenseHat

BASELINE_PATH = Path.home() / "Withers" / "sensor_baseline.json"

# Thresholds (from design decisions)
JOLT_G_THRESHOLD      = 2.0     # accel magnitude > this = jolt
JOLT_COOLDOWN_S       = 5.0     # re-arm after fire
PRESSURE_DROP_HPA_HR  = 1.0     # -1 hPa/hr = storm incoming
MAG_ANOMALY_SIGMAS    = 2.0     # per-axis stdev threshold
DISTURBANCE_DUR_S     = 1.5     # how long quake overlay runs
MAG_ANOMALY_COOLDOWN_S = 8.0    # don't re-trigger too fast

SAMPLE_HZ     = 10.0
SAMPLE_DT     = 1.0 / SAMPLE_HZ
SMOOTHING     = 0.15  # EMA for scalar sensors (low = more stable)
PRESSURE_HISTORY_S = 3600  # 1 hour


class SensorState:
    """All sensor-derived data scenes read from. Updated by SensorThread."""
    def __init__(self):
        # Raw + smoothed scalars
        self.temperature = 25.0      # deg C, EMA-smoothed
        self.humidity = 40.0         # %RH, EMA-smoothed
        self.pressure = 1013.0       # hPa, EMA-smoothed
        # IMU
        self.accel = (0.0, 0.0, 1.0)    # g per axis
        self.accel_magnitude = 1.0
        self.gyro_z = 0.0             # deg/sec
        self.mag = (0.0, 0.0, 0.0)    # uT per axis
        # Baseline (mag only — set by calibrate_baseline)
        self.mag_baseline_mean = None   # (mx, my, mz)
        self.mag_baseline_std  = None   # (sx, sy, sz)
        self.baseline_ready = False
        # Derived event flags
        self.jolt_triggered = False     # scenes/main reset after handling
        self.pressure_drop_active = False
        self.disturbance_active = False
        self.disturbance_t_start = 0.0
        # Internal
        self._jolt_last_fire = 0.0
        self._mag_last_fire = 0.0
        self._pressure_history = deque()  # (t, hPa)

    def tilt(self):
        """Return (x_tilt, y_tilt) in ~[-1, 1] from accelerometer."""
        ax, ay, az = self.accel
        return (max(-1.0, min(1.0, ax)), max(-1.0, min(1.0, ay)))


class SensorThread(threading.Thread):
    """Polls the HAT at 10 Hz, updates state.

    Owns the SenseHat instance for reads. The render Pipeline owns it for writes.
    This dual ownership is safe because sense_hat's underlying I2C calls are
    independent per sensor and the LED matrix uses a separate kernel fb path.
    """
    def __init__(self, state, sense):
        super().__init__(daemon=True, name="sensor-poll")
        self.state = state
        self.sense = sense
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        s = self.state
        while not self._stop.is_set():
            t = time.time()
            # Env sensors (slow, robust reads)
            try:
                temp = self.sense.get_temperature_from_pressure()
                if temp == 0.0:  # RTIMULib invalid flag sentinel
                    temp = s.temperature
                hum = self.sense.get_humidity()
                press = self.sense.get_pressure()
                if press > 0:
                    s.temperature = s.temperature + (temp  - s.temperature) * SMOOTHING
                    s.humidity    = s.humidity    + (hum   - s.humidity)    * SMOOTHING
                    s.pressure    = s.pressure    + (press - s.pressure)    * SMOOTHING
                    # Pressure history
                    s._pressure_history.append((t, s.pressure))
                    while s._pressure_history and t - s._pressure_history[0][0] > PRESSURE_HISTORY_S:
                        s._pressure_history.popleft()
            except Exception:
                pass
            # IMU — accel + gyro (no fusion needed)
            try:
                a = self.sense.get_accelerometer_raw()  # g units
                ax, ay, az = a['x'], a['y'], a['z']
                s.accel = (ax, ay, az)
                mag_a = math.sqrt(ax*ax + ay*ay + az*az)
                s.accel_magnitude = mag_a
                # Jolt detection
                if mag_a > JOLT_G_THRESHOLD and (t - s._jolt_last_fire) > JOLT_COOLDOWN_S:
                    s.jolt_triggered = True
                    s._jolt_last_fire = t
                g = self.sense.get_gyroscope_raw()  # deg/s
                s.gyro_z = g['z']
            except Exception:
                pass
            # Magnetometer
            try:
                m = self.sense.get_compass_raw()  # uT
                mx, my, mz = m['x'], m['y'], m['z']
                s.mag = (mx, my, mz)
                # Anomaly detection against baseline
                if s.baseline_ready and (t - s._mag_last_fire) > MAG_ANOMALY_COOLDOWN_S:
                    mean = s.mag_baseline_mean
                    std  = s.mag_baseline_std
                    deviated = False
                    for i in range(3):
                        if std[i] > 0.1:  # avoid div-by-zero on pathologically still readings
                            if abs((mx, my, mz)[i] - mean[i]) > MAG_ANOMALY_SIGMAS * std[i]:
                                deviated = True; break
                    if deviated:
                        s.disturbance_active = True
                        s.disturbance_t_start = t
                        s._mag_last_fire = t
            except Exception:
                pass
            # Pressure drop analysis
            if len(s._pressure_history) > 30:  # need ~3s of data minimum
                oldest_t, oldest_p = s._pressure_history[0]
                dt_hr = (t - oldest_t) / 3600.0
                if dt_hr > 0.01:  # avoid noise at startup
                    drop_rate = (oldest_p - s.pressure) / dt_hr  # hPa/hour
                    s.pressure_drop_active = drop_rate >= PRESSURE_DROP_HPA_HR
            # Disturbance lifecycle
            if s.disturbance_active and (t - s.disturbance_t_start) > DISTURBANCE_DUR_S:
                s.disturbance_active = False
            # Sleep remainder of tick
            elapsed = time.time() - t
            rem = SAMPLE_DT - elapsed
            if rem > 0:
                self._stop.wait(rem)


def calibrate_baseline(state, sense, duration=30.0, sample_hz=20.0):
    """Blocking: sample magnetometer for `duration` seconds, compute mean+stdev,
    save to disk, populate state. Loads cached baseline if present and fresh.

    Runs on the main thread during the ledger scene. Does NOT drive display.
    The ledger scene renders independently and calls state.baseline_ready
    to know when to wrap.
    """
    # Try cache first (< 7 days old)
    try:
        if BASELINE_PATH.exists():
            with open(BASELINE_PATH) as f:
                cached = json.load(f)
            age = time.time() - cached['saved_at']
            if age < 7 * 86400:
                state.mag_baseline_mean = tuple(cached['mean'])
                state.mag_baseline_std  = tuple(cached['std'])
                state.baseline_ready = True
                return  # quick path — no 30s delay
    except Exception:
        pass
    # Fresh calibration
    samples_x = []; samples_y = []; samples_z = []
    dt = 1.0 / sample_hz
    t_end = time.time() + duration
    while time.time() < t_end:
        try:
            m = sense.get_compass_raw()
            samples_x.append(m['x']); samples_y.append(m['y']); samples_z.append(m['z'])
        except Exception:
            pass
        time.sleep(dt)
    if len(samples_x) < 50:
        # Bad read — fall back to no-anomaly detection
        state.baseline_ready = False
        return
    def _mean(xs): return sum(xs) / len(xs)
    def _std(xs, mu):
        v = sum((x-mu)**2 for x in xs) / len(xs)
        return math.sqrt(max(v, 0.0))
    mx = _mean(samples_x); my = _mean(samples_y); mz = _mean(samples_z)
    sx = _std(samples_x, mx); sy = _std(samples_y, my); sz = _std(samples_z, mz)
    state.mag_baseline_mean = (mx, my, mz)
    state.mag_baseline_std  = (sx, sy, sz)
    state.baseline_ready = True
    try:
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(BASELINE_PATH, 'w') as f:
            json.dump({
                'saved_at': time.time(),
                'mean': [mx, my, mz],
                'std':  [sx, sy, sz],
                'n_samples': len(samples_x),
            }, f, indent=2)
    except Exception:
        pass
