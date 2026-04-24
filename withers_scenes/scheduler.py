"""Markov scene scheduler.

States are thematic categories. Each state contains a set of scenes (with
within-state weights). The chain chooses the next STATE from a transition
matrix, then picks a scene from that state's set (excluding the last-played
scene — anti-repeat).

Events force state jumps:
  - jolt_triggered       -> climactic (judgment)
  - pressure_drop_active -> active     (storm)

After an event resolves, the chain continues from the event's state.
"""
import random

# --- Scene <-> state map ------------------------------------------
# Every scene in REGISTRY except 'ledger' (calibration-only) lives in a state.
STATE_SCENES = {
    'contemplative': {
        'hourglass':     3,
        'orrery':        3,
        'constellation': 3,
        'ripples':       2,
    },
    'active': {
        'wheel':         3,
        'fire':          3,
        'murmuration':   3,
        'storm':         1,
    },
    'inscribing': {
        'quill':         3,
        'sigil':         2,
        'glyphs':        2,
        'recite':        2,
    },
    'climactic': {
        'judgment':      1,
    },
    'observing': {
        'eclipse':       2,
    },
}

# --- Transition matrix --------------------------------------------
# Rows: from state. Cols: to state. Each row sums to 1.0.
TRANSITIONS = {
    'contemplative': {'contemplative': 0.15, 'active': 0.30, 'inscribing': 0.30, 'climactic': 0.05, 'observing': 0.20},
    'active':        {'contemplative': 0.25, 'active': 0.20, 'inscribing': 0.35, 'climactic': 0.15, 'observing': 0.05},
    'inscribing':    {'contemplative': 0.20, 'active': 0.20, 'inscribing': 0.15, 'climactic': 0.30, 'observing': 0.15},
    'climactic':     {'contemplative': 0.70, 'active': 0.10, 'inscribing': 0.05, 'climactic': 0.00, 'observing': 0.15},
    'observing':     {'contemplative': 0.40, 'active': 0.25, 'inscribing': 0.25, 'climactic': 0.05, 'observing': 0.05},
}

# --- Which scene belongs to which state (reverse map) -------------
SCENE_TO_STATE = {scene: state for state, scenes in STATE_SCENES.items() for scene in scenes}


class Scheduler:
    def __init__(self, initial_state='contemplative'):
        self.state = initial_state
        self.last_scene = None

    def _pick_next_state(self):
        row = TRANSITIONS[self.state]
        states = list(row.keys())
        weights = list(row.values())
        return random.choices(states, weights=weights)[0]

    def _pick_scene_from_state(self, state):
        """Pick scene from state, avoiding last_scene if possible."""
        scenes = STATE_SCENES[state]
        names = list(scenes.keys())
        weights = list(scenes.values())
        # Anti-repeat: if state has >1 scene and last_scene is one of them, exclude it
        if len(names) > 1 and self.last_scene in names:
            idx = names.index(self.last_scene)
            names = names[:idx] + names[idx+1:]
            weights = weights[:idx] + weights[idx+1:]
        return random.choices(names, weights=weights)[0]

    def next(self):
        """Advance chain and return next scene name."""
        self.state = self._pick_next_state()
        scene = self._pick_scene_from_state(self.state)
        self.last_scene = scene
        return scene

    def force_state(self, new_state, scene_played):
        """Event forced a scene. Update internal state to match so future
        transitions flow from the event's state, not the pre-event state."""
        self.state = new_state
        self.last_scene = scene_played
