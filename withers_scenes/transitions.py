"""Inter-scene transitions. Each takes (pipe, amb, state, prev_frame, duration)
and renders from prev_frame (snapshot of outgoing scene's last frame) to dark.

Scenes always start themselves from their own opening; transitions cover the gap.
"""
import math, random, time
import numpy as np
from .render import (DT, FPS, BLK, VOID, SHADOW, EMBER, EMBER_HI, AURA_HOT,
                     AURA_CORE, lerp, mul, plot_soft)

def _frame_from_array(arr):
    """uint8 ndarray -> list-of-tuples frame."""
    return [(int(r), int(g), int(b)) for r, g, b in arr.reshape(64, 3)]

def _snapshot_to_array(frame):
    """list-of-tuples frame -> uint8 ndarray (8,8,3)."""
    return np.asarray(frame, dtype=np.float32).reshape(8, 8, 3)

def dissolve(pipe, amb, state, prev_frame, duration=1.2):
    """Crossfade to black via per-pixel luma-dependent timing."""
    src = _snapshot_to_array(prev_frame)
    # Add slight per-pixel noise to timing so pixels fade out in a speckled pattern
    rng = np.random.default_rng()
    offsets = rng.random((8, 8)).astype(np.float32) * 0.35  # each pixel's fade delay fraction
    frames = int(duration * FPS)
    for i in range(frames):
        u = i / frames  # 0 → 1
        # Each pixel's local progress: shifted by its offset, clamped 0-1
        local = np.clip((u - offsets) / (1.0 - offsets.max() + 0.001), 0.0, 1.0)
        arr = src * (1.0 - local[..., None])
        pipe.display(_frame_from_array(arr.astype(np.uint8)), state=state)
        time.sleep(DT)

def iris(pipe, amb, state, prev_frame, duration=1.0):
    """Circle of darkness closes inward from edges."""
    src = _snapshot_to_array(prev_frame)
    cy, cx = np.mgrid[0:8, 0:8]
    dist = np.sqrt((cx - 3.5)**2 + (cy - 3.5)**2).astype(np.float32)
    max_d = float(dist.max())
    frames = int(duration * FPS)
    for i in range(frames):
        u = i / frames
        # Radius of visible area shrinks from max_d → 0
        visible_r = max_d * (1.0 - u)
        # Soft edge: 1.0 inside, falls off over 0.8px
        mask = np.clip(1.0 - (dist - visible_r + 0.4) / 0.8, 0.0, 1.0)
        arr = src * mask[..., None]
        pipe.display(_frame_from_array(arr.astype(np.uint8)), state=state)
        time.sleep(DT)

def wipe(pipe, amb, state, prev_frame, duration=0.9):
    """Horizontal sweep: pixels go black from left to right (or right to left)."""
    src = _snapshot_to_array(prev_frame)
    direction = random.choice([1, -1])  # 1 = L→R, -1 = R→L
    frames = int(duration * FPS)
    for i in range(frames):
        u = i / frames
        # Leading edge position (0 → 9 to fully clear)
        edge = u * 9.0 - 0.5
        if direction == -1:
            edge = 8.5 - edge
        cols = np.arange(8).astype(np.float32)
        if direction == 1:
            mask = np.clip(edge - cols, 0.0, 1.0)  # 1 where already swept
        else:
            mask = np.clip(cols - edge, 0.0, 1.0)
        # Invert: we want "remaining visible" = 1 - mask
        visible = 1.0 - mask
        arr = src * visible[None, :, None]  # broadcast across rows/channels
        pipe.display(_frame_from_array(arr.astype(np.uint8)), state=state)
        time.sleep(DT)

def particle_dissolve(pipe, amb, state, prev_frame, duration=1.5):
    """Each bright pixel's color is ejected as a flying ember; frame darkens behind."""
    src = _snapshot_to_array(prev_frame)
    # Pick bright pixels to launch
    L = src @ np.array([0.3, 0.5, 0.2], dtype=np.float32)
    bright_mask = L > 25.0
    particles = []
    for r in range(8):
        for c in range(8):
            if bright_mask[r, c]:
                col = tuple(int(v) for v in src[r, c])
                angle = math.atan2(r - 3.5, c - 3.5)
                speed = random.uniform(2.0, 4.5)
                particles.append({
                    'x': float(c), 'y': float(r),
                    'vx': math.cos(angle) * speed + random.uniform(-0.5, 0.5),
                    'vy': math.sin(angle) * speed + random.uniform(-0.5, 0.5),
                    'color': col,
                    'life': random.uniform(0.8, 1.3),
                    'age': 0.0,
                })
    frames = int(duration * FPS)
    for i in range(frames):
        u = i / frames
        # Base frame: source darkening
        darken = 1.0 - min(1.0, u * 1.8)
        arr = src * darken
        # Advance and render particles
        remaining = []
        for p in particles:
            p['age'] += DT
            if p['age'] >= p['life']:
                continue
            p['x'] += p['vx'] * DT
            p['y'] += p['vy'] * DT
            remaining.append(p)
            # Render into arr as additive plot
            b = 1.0 - (p['age'] / p['life'])
            xi, yi = int(round(p['x'])), int(round(p['y']))
            if 0 <= xi < 8 and 0 <= yi < 8:
                arr[yi, xi, 0] = min(255, arr[yi, xi, 0] + p['color'][0] * b * 0.9)
                arr[yi, xi, 1] = min(255, arr[yi, xi, 1] + p['color'][1] * b * 0.9)
                arr[yi, xi, 2] = min(255, arr[yi, xi, 2] + p['color'][2] * b * 0.9)
        particles = remaining
        np.clip(arr, 0, 255, out=arr)
        pipe.display(_frame_from_array(arr.astype(np.uint8)), state=state)
        time.sleep(DT)

STYLES = [dissolve, iris, wipe, particle_dissolve]

def random_transition(pipe, amb, state, prev_frame):
    """Pick a style and run it. Scene code calls this between scenes."""
    fn = random.choice(STYLES)
    fn(pipe, amb, state, prev_frame)
