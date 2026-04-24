"""Entry point: sensor thread, calibration, scene scheduler with transitions."""
import random, signal, sys, time, threading
from .render import Pipeline
from .ambient import AmbientLayer
from .scenes import ledger, entrance, idle, judgment, storm, REGISTRY
from .sensors import SensorState, SensorThread, calibrate_baseline
from .transitions import random_transition


def main():
    pipe = Pipeline()
    state = SensorState()
    amb = AmbientLayer(state=state)

    sensor_thread = SensorThread(state, pipe.sense)
    sensor_thread.start()

    def extinguish(*_):
        sensor_thread.stop()
        pipe.clear()
        sys.exit(0)
    signal.signal(signal.SIGINT, extinguish)
    signal.signal(signal.SIGTERM, extinguish)

    cal_thread = threading.Thread(
        target=calibrate_baseline,
        args=(state, pipe.sense),
        daemon=True, name="mag-calibrate",
    )
    cal_thread.start()

    ledger(pipe, amb, state=state)
    cal_thread.join(timeout=1.0)
    entrance(pipe, amb, state=state)
    # First transition from entrance
    random_transition(pipe, amb, state, pipe.last_frame)

    names = [r[0] for r in REGISTRY]
    fns = {r[0]: r[1] for r in REGISTRY}
    weights = {r[0]: r[2] for r in REGISTRY}
    last = None

    while True:
        # Jolt interrupt
        if state.jolt_triggered:
            state.jolt_triggered = False
            random_transition(pipe, amb, state, pipe.last_frame)
            amb.clear_motes()
            judgment(pipe, amb, state=state)
            idle(pipe, amb, random.uniform(1.0, 2.0), state=state)
            random_transition(pipe, amb, state, pipe.last_frame)
            last = 'judgment'
            continue

        # Pressure drop
        if state.pressure_drop_active and last != 'storm':
            storm(pipe, amb, state=state)
            random_transition(pipe, amb, state, pipe.last_frame)
            last = 'storm'
            continue

        # Normal weighted random
        choices = [n for n in names if n != last]
        ws = [weights[n] for n in choices]
        pick = random.choices(choices, weights=ws)[0]
        fns[pick](pipe, amb, state=state)
        random_transition(pipe, amb, state, pipe.last_frame)
        last = pick


if __name__ == '__main__':
    main()
