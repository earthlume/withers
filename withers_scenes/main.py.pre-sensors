"""Entry point: orchestrates the scene loop."""
import signal, sys, random, time
from .render import Pipeline
from .ambient import AmbientLayer
from .scenes import entrance, idle, REGISTRY

def main():
    pipe = Pipeline()
    amb = AmbientLayer()

    def extinguish(*_):
        pipe.clear(); sys.exit(0)
    signal.signal(signal.SIGINT, extinguish)
    signal.signal(signal.SIGTERM, extinguish)

    entrance(pipe, amb)
    idle(pipe, amb, 1.2)

    names = [r[0] for r in REGISTRY]
    fns = {r[0]: r[1] for r in REGISTRY}
    weights = {r[0]: r[2] for r in REGISTRY}
    last = None
    while True:
        choices = [n for n in names if n != last]
        ws = [weights[n] for n in choices]
        pick = random.choices(choices, weights=ws)[0]
        fns[pick](pipe, amb)
        last = pick
        idle(pipe, amb, random.uniform(1.2, 2.5))

if __name__ == '__main__':
    main()
