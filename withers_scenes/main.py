"""Entry point: sensor thread, calibration, Markov scheduler, storage, web dashboard."""
import random, signal, sys, threading, time
from .render import Pipeline
from .ambient import AmbientLayer
from .scenes import ledger, entrance, idle, judgment, storm, REGISTRY
from .sensors import SensorState, SensorThread, calibrate_baseline
from .transitions import random_transition
from .scheduler import Scheduler
from .storage import WriterThread, record_sensor, record_scene, record_event
from .web import start_web_thread


def main():
    pipe = Pipeline()
    state = SensorState()
    amb = AmbientLayer(state=state)
    start_ts = time.time()

    sensor_thread = SensorThread(state, pipe.sense)
    sensor_thread.start()
    writer_thread = WriterThread()
    writer_thread.start()

    # Sensor samples -> DB @ 1 Hz
    def sample_loop():
        while True:
            time.sleep(1.0)
            record_sensor(state)
    threading.Thread(target=sample_loop, daemon=True, name="db-sampler").start()

    # Shared state for the web dashboard
    sched = Scheduler(initial_state='contemplative')
    shared = {'state': state, 'pipe': pipe, 'sched': sched, 'start_ts': start_ts}
    start_web_thread(shared)

    def extinguish(*_):
        sensor_thread.stop()
        writer_thread.stop()
        pipe.clear()
        sys.exit(0)
    signal.signal(signal.SIGINT, extinguish)
    signal.signal(signal.SIGTERM, extinguish)

    # Calibration during ledger
    cal_thread = threading.Thread(
        target=calibrate_baseline,
        args=(state, pipe.sense),
        daemon=True, name="mag-calibrate",
    )
    cal_thread.start()
    ledger(pipe, amb, state=state)
    cal_thread.join(timeout=1.0)

    entrance(pipe, amb, state=state)
    random_transition(pipe, amb, state, pipe.last_frame)

    fns = {r[0]: r[1] for r in REGISTRY}

    def play_and_record(scene_name):
        fns[scene_name](pipe, amb, state=state)
        record_scene(scene_name, sched.state)

    while True:
        # Jolt interrupt — forces climactic
        if state.jolt_triggered:
            state.jolt_triggered = False
            record_event('jolt', f'mag={state.accel_magnitude:.2f}g')
            random_transition(pipe, amb, state, pipe.last_frame)
            amb.clear_motes()
            judgment(pipe, amb, state=state)
            sched.force_state('climactic', 'judgment')
            record_scene('judgment', 'climactic')
            idle(pipe, amb, random.uniform(1.0, 2.0), state=state)
            random_transition(pipe, amb, state, pipe.last_frame)
            continue

        # Pressure drop — forces active via storm
        if state.pressure_drop_active and sched.last_scene != 'storm':
            record_event('pressure_drop', f'p={state.pressure:.2f}hPa')
            storm(pipe, amb, state=state)
            sched.force_state('active', 'storm')
            record_scene('storm', 'active')
            random_transition(pipe, amb, state, pipe.last_frame)
            continue

        # Disturbance (mag anomaly) already renders via quake overlay — just log
        if state.disturbance_active and time.time() - state.disturbance_t_start < 0.2:
            record_event('disturbance', f'mag={state.mag}')

        scene_name = sched.next()
        play_and_record(scene_name)
        random_transition(pipe, amb, state, pipe.last_frame)


if __name__ == '__main__':
    main()
