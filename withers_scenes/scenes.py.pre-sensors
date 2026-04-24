"""All scenes. Each takes (pipeline, ambient) and runs to completion."""
import math, random, time
from .render import (FPS, DT, BLK, VOID, SHADOW, SHADOW_HI, AURA_DIM, AURA_MID,
                     AURA_HOT, AURA_CORE, INK, INK_HOT, GLYPH, GLYPH_HOT,
                     GLASS, GLASS_HI, SAND, SAND_HI, THREAD, FIRE_LO, FIRE_MID,
                     FIRE_HI, FIRE_TOP, VERDICT, SIGIL_COLD, SIGIL_HOT,
                     ORBIT_A, ORBIT_B, ORBIT_C,
                     lerp, mul, screen, plot_soft, draw_line, text_cols)
from .ambient import full_bg

QUOTES = [
    "FATE SPINS ALONG.",
    "A SERVANT TO OBLIGATION.",
    "THINE ACTIONS ARE NOTED.",
    "NONE IS EVER LOST.",
    "ARBITER OF FATE.",
    "THOU HAST RETURNED.",
    "IT IS NOT YET THY TIME.",
    "THE LEDGER REMEMBERS.",
    "HARK.",
    "A BOON, THEN.",
    "THY DEBT IS MARKED.",
    "THE QUILL DOES NOT TIRE.",
]

def entrance(pipe, amb):
    duration = 5.5; start = time.time(); pipe.reset_blur()
    while True:
        el = time.time() - start
        if el >= duration: break
        t = time.time(); u = el/duration; eased = 1-(1-u)**3
        frame = [lerp(VOID, SHADOW, eased*0.6)] * 64
        size_sq = 2*(0.5 + eased*1.8)**2
        for r in range(8):
            for c in range(8):
                d_sq = (c-3.5)**2 + (r-3.5)**2
                glow = math.exp(-d_sq / size_sq) * eased
                if glow > 0.04:
                    col = lerp(AURA_MID, AURA_CORE, eased)
                    frame[r*8+c] = screen(frame[r*8+c], mul(col, glow*0.95))
        amb.tick(frame, spawn_dust=(eased>0.2), wisp_chance=0)
        pipe.display(frame); time.sleep(DT)

def idle(pipe, amb, duration):
    start = time.time()
    while time.time() - start < duration:
        t = time.time(); frame = full_bg(t)
        amb.tick(frame, wisp_chance=0.015)
        pipe.display(frame); time.sleep(DT)

# --- Hourglass ----------------------------------------------------
HG_WALL = [
    [1,1,1,1,1,1,1,1],[1,0,0,0,0,0,0,1],[0,1,0,0,0,0,1,0],
    [0,0,1,0,0,1,0,0],[0,0,1,0,0,1,0,0],[0,1,0,0,0,0,1,0],
    [1,0,0,0,0,0,0,1],[1,1,1,1,1,1,1,1],
]
def _hg_open(r, c): return 0<=r<8 and 0<=c<8 and not HG_WALL[r][c]
def _hg_top(r, c):  return _hg_open(r, c) and r < 4

class _Grain:
    def __init__(self, x, y, top=True):
        self.x=float(x); self.y=float(y); self.vx=0.0; self.vy=0.0
        self.top=top; self.settled=False
    def step(self, occupied):
        if self.settled: return
        self.vy = min(self.vy + 25*DT, 8.0)
        self.vx *= 0.85
        tr, tc = int(round(self.y + self.vy*DT)), int(round(self.x))
        if _hg_open(tr, tc) and (tr, tc) not in occupied:
            self.y += self.vy*DT
        else:
            tr2 = int(round(self.y + 1))
            for dc in random.sample([-1, 1], 2):
                tc2 = int(round(self.x + dc))
                if _hg_open(tr2, tc2) and (tr2, tc2) not in occupied:
                    self.x += dc * 0.7; self.y = tr2; self.vy = 0; break
            else:
                self.settled = True; self.vy = 0
                self.y = round(self.y); self.x = round(self.x)

def hourglass(pipe, amb):
    duration = 12.0; start = time.time(); pipe.reset_blur()
    grains = []
    top_cells = [(r,c) for r in range(8) for c in range(8) if _hg_top(r,c)]
    random.shuffle(top_cells); settled_top = set()
    for (r, c) in top_cells[:10]:
        g = _Grain(c, r, top=True); g.settled = True
        grains.append(g); settled_top.add((r, c))
    last_drop = start
    while True:
        el = time.time() - start
        if el > duration: break
        t = time.time()
        if el < duration - 2.0 and (t - last_drop) > 0.35 and settled_top:
            (sr, sc) = max(settled_top, key=lambda k: k[0])
            settled_top.discard((sr, sc))
            for g in grains:
                if g.settled and g.top and int(round(g.y))==sr and int(round(g.x))==sc:
                    grains.remove(g); break
            grains.append(_Grain(3 + random.randint(0,1), 3, top=False))
            last_drop = t
        occupied = set()
        for g in grains:
            if g.settled: occupied.add((int(round(g.y)), int(round(g.x))))
        for g in grains:
            if not g.settled:
                g.step(occupied)
                if g.settled: occupied.add((int(round(g.y)), int(round(g.x))))
        frame = full_bg(t, strength=0.7)
        for r in range(8):
            for c in range(8):
                if HG_WALL[r][c]:
                    shim = 0.85 + 0.15*math.sin(t*1.5 + r*0.4 + c*0.3)
                    frame[r*8+c] = lerp(GLASS, GLASS_HI, shim)
        for g in grains:
            shim = 0.9 + 0.1*math.sin(t*3 + g.x + g.y)
            plot_soft(frame, g.x, g.y, lerp(SAND, SAND_HI, shim),
                      1.0 if g.settled else 1.2)
        amb.tick(frame, wisp_chance=0.002)
        pipe.display(frame); time.sleep(DT)

# --- Wheel --------------------------------------------------------
def wheel(pipe, amb):
    duration = 10.0; start = time.time(); pipe.reset_blur()
    while True:
        el = time.time() - start
        if el > duration: break
        t = time.time(); frame = full_bg(t)
        op = el * (2*math.pi / 6)
        for i in range(8):
            a = i*(2*math.pi/8) + op
            plot_soft(frame, 3.5+3.3*math.cos(a), 3.5+3.3*math.sin(a), AURA_MID, 0.9)
            plot_soft(frame, 3.5+3.3*math.cos(a-0.18), 3.5+3.3*math.sin(a-0.18), AURA_MID, 0.4)
        mp = -el * (2*math.pi / 4)
        for i in range(6):
            a = i*(2*math.pi/6) + mp
            plot_soft(frame, 3.5+2.0*math.cos(a), 3.5+2.0*math.sin(a), AURA_HOT, 1.0)
            plot_soft(frame, 3.5+2.0*math.cos(a+0.25), 3.5+2.0*math.sin(a+0.25), AURA_HOT, 0.4)
        ip = el * (2*math.pi / 2)
        for i in range(4):
            a = i*(2*math.pi/4) + ip
            plot_soft(frame, 3.5+0.9*math.cos(a), 3.5+0.9*math.sin(a), AURA_CORE, 1.0)
        plot_soft(frame, 3.5, 3.5, AURA_CORE, 0.6)
        align = (el % 2.2) / 2.2
        if align < 0.15:
            s = math.sin(align * (math.pi/0.15))
            if s > 0:
                for i in range(4):
                    a = i*(2*math.pi/4) + ip
                    for step_i in range(1, 4):
                        rs = step_i * 0.75
                        plot_soft(frame, 3.5+rs*math.cos(a), 3.5+rs*math.sin(a),
                                  AURA_HOT, s*0.5)
        amb.tick(frame, wisp_chance=0.002)
        pipe.display(frame); time.sleep(DT)

# --- Ripples ------------------------------------------------------
def ripples(pipe, amb):
    duration = 11.0; start = time.time(); last_wave = start - 1.5; waves = []
    pipe.reset_blur()
    while True:
        el = time.time() - start
        if el > duration: break
        t = time.time()
        if t - last_wave > 1.8:
            waves.append((t, random.uniform(1.5,6.5), random.uniform(1.5,6.5)))
            last_wave = t
        waves = [(st, cx, cy) for (st, cx, cy) in waves if t - st < 6.0]
        frame = full_bg(t)
        for r in range(8):
            for c in range(8):
                acc = 0.0
                for (wst, cx, cy) in waves:
                    age = t - wst
                    amp = max(0, 1 - age/6.0)
                    d = math.hypot(c - cx, r - cy)
                    acc += max(0, 1 - abs(d - age*1.6)*1.2) * amp
                if acc > 0.02:
                    col = lerp(AURA_HOT, AURA_CORE, min(1, acc*0.7))
                    frame[r*8+c] = screen(frame[r*8+c], mul(col, min(1, acc*0.85)))
        amb.tick(frame, wisp_chance=0.003)
        pipe.display(frame); time.sleep(DT)

# --- Quill --------------------------------------------------------
def quill(pipe, amb):
    duration = 14.0; start = time.time()
    cx = 0.0; cy = 2; marks = {}; pipe.reset_blur()
    while True:
        el = time.time() - start
        if el > duration: break
        t = time.time()
        cx += 2.4 * DT
        if cx >= 8:
            cx = 0; cy += 1
            if cy > 5:
                new = {}
                for (r,c),(pt,b) in marks.items():
                    if r-1 >= 0: new[(r-1,c)] = (pt, b*0.65)
                marks = new; cy = 5
        if random.random() < 0.38:
            key = (cy, int(cx))
            if key not in marks: marks[key] = (t, 1.0)
        frame = full_bg(t, strength=0.7)
        for (r, c), (pt, b) in marks.items():
            inten = b * min(1, (t - pt)/0.2)
            frame[r*8+c] = screen(frame[r*8+c], mul(INK, inten*0.9))
        plot_soft(frame, cx, cy, INK_HOT, 1.0)
        plot_soft(frame, cx, cy-1, INK_HOT, 0.35)
        plot_soft(frame, cx-0.6, cy-0.4, INK_HOT, 0.25)
        amb.tick(frame, wisp_chance=0)
        pipe.display(frame); time.sleep(DT)

# --- Sigil --------------------------------------------------------
SIGILS = [
    [[0,0,0,1,1,0,0,0],[0,0,1,0,0,1,0,0],[1,1,1,0,0,1,1,1],
     [0,0,0,1,1,0,0,0],[0,0,0,1,1,0,0,0],[1,1,1,0,0,1,1,1],
     [0,0,1,0,0,1,0,0],[0,0,0,1,1,0,0,0]],
    [[0,0,1,1,1,1,0,0],[0,1,0,0,0,0,1,0],[1,0,0,1,1,0,0,1],
     [1,0,1,0,0,1,0,1],[1,0,1,0,0,1,0,1],[1,0,0,1,1,0,0,1],
     [0,1,0,0,0,0,1,0],[0,0,1,1,1,1,0,0]],
    [[0,1,1,1,1,1,1,0],[1,0,0,0,0,0,0,1],[1,0,0,1,1,0,0,1],
     [1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1],[1,0,0,1,1,0,0,1],
     [1,0,0,0,0,0,0,1],[0,1,1,1,1,1,1,0]],
    [[1,1,1,1,1,1,1,1],[0,1,0,0,0,0,1,0],[0,1,0,1,1,0,1,0],
     [0,0,1,1,1,1,0,0],[0,0,0,1,1,0,0,0],[0,0,0,1,1,0,0,0],
     [0,0,0,0,1,0,0,0],[0,0,0,1,0,0,0,0]],
]
def sigil(pipe, amb):
    sig = random.choice(SIGILS)
    pixels = [(r, c) for r in range(8) for c in range(8) if sig[r][c]]
    if not pixels: return
    ordered = [pixels.pop(0)]
    while pixels:
        last_p = ordered[-1]
        nearest = min(range(len(pixels)),
                      key=lambda i: (pixels[i][0]-last_p[0])**2 + (pixels[i][1]-last_p[1])**2)
        ordered.append(pixels.pop(nearest))
    DRAW_DUR = 4.5; HOLD = 2.5; FADE = 1.5
    revealed = {}; s0 = time.time(); pipe.reset_blur()
    pos = (ordered[0][1], ordered[0][0])
    prev_target_t = s0
    for i, (r, c) in enumerate(ordered):
        target = s0 + (i/len(ordered))*DRAW_DUR
        target_pos = (c, r)
        while time.time() < target:
            t = time.time()
            denom = max(0.001, target - prev_target_t)
            frac = max(0, min(1, (t - prev_target_t) / denom))
            px = pos[0] + (target_pos[0] - pos[0]) * frac
            py = pos[1] + (target_pos[1] - pos[1]) * frac
            frame = full_bg(t, strength=0.6)
            for (rr, cc), pt in revealed.items():
                b = min(1.0, (t-pt)/0.25)
                frame[rr*8+cc] = screen(frame[rr*8+cc], mul(SIGIL_COLD, b))
            plot_soft(frame, px, py, SIGIL_HOT, 1.0)
            plot_soft(frame, px, py-0.5, SIGIL_HOT, 0.3)
            plot_soft(frame, px, py+0.5, SIGIL_HOT, 0.3)
            amb.tick(frame, wisp_chance=0)
            pipe.display(frame); time.sleep(DT)
        revealed[(r, c)] = time.time()
        pos = target_pos; prev_target_t = target
    hs = time.time()
    while time.time() - hs < HOLD:
        t = time.time(); pulse = 0.85 + 0.15*math.sin((t-hs)*3)
        frame = full_bg(t, strength=0.6)
        for (rr, cc) in revealed:
            frame[rr*8+cc] = screen(frame[rr*8+cc], mul(SIGIL_HOT, pulse))
        amb.tick(frame, wisp_chance=0)
        pipe.display(frame); time.sleep(DT)
    fs = time.time()
    while time.time() - fs < FADE:
        t = time.time(); fp = (t-fs)/FADE
        frame = full_bg(t, strength=0.6)
        for (rr, cc) in revealed:
            frame[rr*8+cc] = screen(frame[rr*8+cc], mul(SIGIL_COLD, max(0,1-fp)))
        amb.tick(frame, wisp_chance=0)
        pipe.display(frame); time.sleep(DT)

# --- Constellation ------------------------------------------------
def constellation(pipe, amb):
    N = random.randint(5, 7); stars = []
    while len(stars) < N:
        x = random.uniform(0.8, 7.2); y = random.uniform(0.8, 7.2)
        if all(math.hypot(sx-x, sy-y) > 1.7 for sx, sy in stars):
            stars.append((x, y))
    order = list(range(N)); random.shuffle(order)
    reveal = {}; pipe.reset_blur()
    def render(lines, fade=1.0):
        t = time.time(); frame = full_bg(t, strength=0.65)
        for (i1, i2, lst, ldur) in lines:
            p = min(1.0, (t-lst)/ldur)
            x0,y0 = stars[i1]; x1,y1 = stars[i2]
            draw_line(frame, x0, y0, x0+(x1-x0)*p, y0+(y1-y0)*p, THREAD, 0.45*fade)
        for idx, (x, y) in enumerate(stars):
            if idx in reveal:
                b = min(1.0, (t-reveal[idx])/0.4)
                tw = 0.8 + 0.2*math.sin(t*3 + idx)
                plot_soft(frame, x, y, AURA_CORE, b*tw*fade)
        amb.tick(frame, wisp_chance=0.002)
        pipe.display(frame); time.sleep(DT)
    s0 = time.time()
    for i, idx in enumerate(order):
        while time.time() < s0 + i*0.45: render([])
        reveal[idx] = time.time()
    lines = []
    for i in range(N-1):
        lst = time.time()
        lines.append((order[i], order[i+1], lst, 0.7))
        while time.time() - lst < 0.7: render(lines)
    hs = time.time()
    while time.time() - hs < 2.5: render(lines)
    fs = time.time()
    while time.time() - fs < 1.5:
        render(lines, fade=max(0, 1 - (time.time()-fs)/1.5))

# --- Glyphs -------------------------------------------------------
GLYPHS = [
    [[1,0,0,0,1],[0,1,0,1,0],[0,0,1,0,0],[0,0,1,0,0],
     [0,0,1,0,0],[0,0,1,0,0],[0,1,1,1,0],[0,0,0,0,0]],
    [[0,0,0,0,0],[0,1,1,1,0],[1,0,0,0,1],[1,0,1,0,1],
     [1,0,0,0,1],[0,1,1,1,0],[0,0,1,0,0],[0,0,0,0,0]],
    [[1,0,1,0,1],[1,0,1,0,1],[1,0,1,0,1],[1,1,1,1,1],
     [0,0,1,0,0],[0,0,1,0,0],[0,0,1,0,0],[0,1,1,1,0]],
    [[0,0,1,0,0],[0,1,1,1,0],[1,1,0,1,1],[0,1,0,1,0],
     [0,1,0,1,0],[0,1,0,1,0],[1,1,0,1,1],[0,0,0,0,0]],
    [[1,0,0,0,1],[0,1,1,1,0],[1,1,0,1,1],[0,1,0,1,0],
     [1,1,0,1,1],[0,1,1,1,0],[0,0,1,0,0],[0,0,1,0,0]],
]
def glyphs(pipe, amb):
    chosen = random.sample(GLYPHS, min(3, len(GLYPHS)))
    strip = [[0]*8 for _ in range(8)]
    for gi, g in enumerate(chosen):
        for r in range(8):
            for c in range(5): strip[r].append(g[r][c])
            if gi < len(chosen)-1:
                for _ in range(3): strip[r].append(0)
    for r in range(8): strip[r].extend([0]*8)
    width = len(strip[0]); SUB = 10; pipe.reset_blur()
    for i in range((width - 8) * SUB):
        t = time.time(); off = i // SUB; fine = (i % SUB) / SUB
        frame = full_bg(t, strength=0.65)
        for c in range(8):
            for r in range(8):
                v = strip[r][off+c]*(1-fine) + strip[r][min(off+c+1, width-1)]*fine
                if v > 0.05:
                    shim = 0.85 + 0.15*math.sin(t*2 + r*0.5 + c*0.3)
                    col = lerp(GLYPH, GLYPH_HOT, shim)
                    frame[r*8+c] = screen(frame[r*8+c], mul(col, v*shim))
        amb.tick(frame, wisp_chance=0)
        pipe.display(frame); time.sleep(DT)

# --- Fire ---------------------------------------------------------
def fire(pipe, amb):
    duration = 10.0; start = time.time()
    H = 10; heat = [[0.0]*8 for _ in range(H)]
    STOPS = [(0.0, FIRE_LO), (0.35, FIRE_MID), (0.65, FIRE_HI), (1.0, FIRE_TOP)]
    def fc(v):
        if v <= 0: return BLK
        v = min(1.0, v)
        for i in range(len(STOPS)-1):
            s0, c0 = STOPS[i]; s1, c1 = STOPS[i+1]
            if v <= s1: return lerp(c0, c1, (v - s0) / (s1 - s0))
        return FIRE_TOP
    pipe.reset_blur()
    while True:
        el = time.time() - start
        if el > duration: break
        t = time.time()
        intensity = 1.0 if el < duration - 2 else max(0.2, 1 - (el - (duration-2))/2)
        for c in range(8):
            heat[H-1][c] = random.uniform(0.55, 1.0) * intensity
            heat[H-2][c] = max(heat[H-2][c], random.uniform(0.4, 0.8) * intensity)
        new_heat = [[0.0]*8 for _ in range(H)]
        new_heat[H-1] = heat[H-1][:]; new_heat[H-2] = heat[H-2][:]
        for r in range(H-3, -1, -1):
            for c in range(8):
                sides = [heat[r+1][c]]
                if c > 0: sides.append(heat[r+1][c-1])
                if c < 7: sides.append(heat[r+1][c+1])
                sides.append(heat[r+2][c])
                avg = sum(sides) / len(sides)
                decay = 1.0 - (0.055 + random.uniform(-0.02, 0.02))
                drift = random.choice([-1, 0, 0, 1])
                sc = c + drift
                if 0 <= sc < 8:
                    new_heat[r][sc] = max(new_heat[r][sc], avg * decay)
                else:
                    new_heat[r][c] = max(new_heat[r][c], avg * decay)
        heat = new_heat
        frame = [VOID] * 64
        for r in range(8):
            for c in range(8):
                v = heat[r][c]
                if v > 0.02: frame[r*8+c] = fc(v)
        if random.random() < 0.3:
            amb.spawn_mote(random.uniform(1.5, 6.5), 1.0)
            amb.motes[-1].vy = random.uniform(-2.5, -1.5)
        amb.tick(frame, spawn_dust=False, wisp_chance=0)
        pipe.display(frame); time.sleep(DT)
    amb.clear_motes()

# --- Orrery -------------------------------------------------------
def orrery(pipe, amb):
    duration = 12.0; start = time.time(); pipe.reset_blur()
    bodies = [
        (3.0, 0.6, 0.0, ORBIT_A),
        (1.8, 1.4, math.pi/3, ORBIT_B),
        (0.8, 2.5, math.pi, ORBIT_C),
    ]
    trails = [[] for _ in bodies]
    TRAIL_LIFE = 1.8
    while True:
        el = time.time() - start
        if el > duration: break
        t = time.time(); frame = full_bg(t, strength=0.6)
        sun_pulse = 0.85 + 0.15*math.sin(t*1.2)
        plot_soft(frame, 3.5, 3.5, mul(AURA_CORE, sun_pulse), 1.0)
        positions = []
        for i, (radius, speed, phase, color) in enumerate(bodies):
            a = el * speed + phase
            bx = 3.5 + radius * math.cos(a); by = 3.5 + radius * math.sin(a)
            positions.append((bx, by))
            trails[i].append((bx, by, t))
            trails[i] = [(x,y,pt) for (x,y,pt) in trails[i] if t - pt < TRAIL_LIFE]
            for (tx, ty, pt) in trails[i]:
                fade = max(0, 1 - (t - pt)/TRAIL_LIFE) * 0.4
                plot_soft(frame, tx, ty, color, fade)
            plot_soft(frame, bx, by, color, 1.0)
            plot_soft(frame, bx+0.4, by, color, 0.2)
            plot_soft(frame, bx-0.4, by, color, 0.2)
        for i in range(len(positions)):
            for j in range(i+1, len(positions)):
                d = math.hypot(positions[i][0]-positions[j][0], positions[i][1]-positions[j][1])
                if d < 0.8:
                    mx = (positions[i][0] + positions[j][0]) / 2
                    my = (positions[i][1] + positions[j][1]) / 2
                    plot_soft(frame, mx, my, AURA_CORE, (1 - d/0.8) * 0.6)
        amb.tick(frame, wisp_chance=0.002)
        pipe.display(frame); time.sleep(DT)

# --- Recite -------------------------------------------------------
def recite(pipe, amb):
    quote = random.choice(QUOTES); pipe.reset_blur()
    for i in range(int(1.3 * FPS)):
        u = i / (1.3*FPS); frame = [VOID] * 64
        for r in range(8):
            for c in range(8):
                d_sq = (c-3.5)**2 + (r-3.5)**2
                glow = math.exp(-d_sq / 4.0) * u * 0.75
                frame[r*8+c] = screen(frame[r*8+c], mul(AURA_DIM, glow))
        pipe.display(frame); time.sleep(DT)
    pipe.reset_blur()
    SUB = 14; pre, post = 10, 9
    cols = [[0]*8 for _ in range(pre)] + text_cols(quote) + [[0]*8 for _ in range(post)]
    width = len(cols)
    for i in range((width - 8) * SUB):
        t = time.time(); off = i // SUB; fine = (i % SUB) / SUB
        frame = [BLK] * 64
        for (cr, cc) in [(0,0),(0,7),(7,0),(7,7)]:
            fl = 0.6 + 0.4*math.sin(t*2 + cr + cc)
            frame[cr*8+cc] = mul(AURA_DIM, fl)
        for c in range(8):
            for r in range(8):
                v = cols[off+c][r]*(1-fine) + cols[min(off+c+1, width-1)][r]*fine
                if v > 0.05:
                    frame[r*8+c] = lerp(frame[r*8+c], INK_HOT, v)
        pipe.display(frame, do_blur=False); time.sleep(DT)
    pipe.reset_blur()
    for i in range(int(2.0 * FPS)):
        t = time.time(); u = i / (2.0*FPS)
        frame = full_bg(t, strength=0.7)
        for r in range(8):
            for c in range(8):
                d_sq = (c-3.5)**2 + (r-3.5)**2
                glow = math.exp(-d_sq / 4.0) * 0.5 * (1 - u)
                frame[r*8+c] = screen(frame[r*8+c], mul(AURA_MID, glow))
        pipe.display(frame); time.sleep(DT)

from .render import text_cols  # ensure imported

# --- Judgment -----------------------------------------------------
def judgment(pipe, amb):
    pipe.reset_blur()
    tf = int(1.5 * FPS)
    for i in range(tf):
        t = time.time(); amp = (i/tf)**1.5
        jx = amp * (random.random()-0.5) * 0.8
        jy = amp * (random.random()-0.5) * 0.8
        frame = full_bg(t)
        size_sq = (3.0 - 1.5*amp)**2
        for r in range(8):
            for c in range(8):
                d_sq = (c-3.5-jx)**2 + (r-3.5-jy)**2
                glow = math.exp(-d_sq / size_sq) * (0.5 + amp)
                col = lerp(AURA_HOT, VERDICT, amp)
                frame[r*8+c] = screen(frame[r*8+c], mul(col, min(1.0, glow)))
        if random.random() < amp * 0.5:
            amb.spawn_mote(3.5+jx, 3.5+jy)
        amb.tick(frame, wisp_chance=0)
        pipe.display(frame); time.sleep(DT)
    for i in range(int(0.9 * FPS)):
        u = i/(0.9*FPS); ring_r = u * 5.8; base_v = u * 0.45
        frame = []
        for r in range(8):
            for c in range(8):
                d = math.hypot(c - 3.5, r - 3.5)
                ri = max(0, 1 - abs(d - ring_r)*0.8) * (1 - u*0.3)
                base = lerp(VOID, AURA_HOT, base_v)
                frame.append(lerp(base, VERDICT, ri))
        pipe.display(frame); time.sleep(DT)
    for _ in range(int(0.2*FPS)):
        pipe.sense.set_pixels([VERDICT] * 64); time.sleep(DT)
    max_d = math.hypot(3.5, 3.5)
    for step_i in range(int(1.3*FPS)):
        tt = step_i / (1.3*FPS)
        frame = []
        for r in range(8):
            for c in range(8):
                d = math.hypot(c - 3.5, r - 3.5)
                local = max(0, min(1, tt*2.2 - d/max_d*1.3))
                frame.append(lerp(VERDICT, VOID, local))
        pipe.display(frame, do_blur=False); time.sleep(DT)
    pipe.reset_blur()
    for _ in range(int(1.0 * FPS)):
        frame = [mul(VOID, 0.3)] * 64
        amb.tick(frame, wisp_chance=0)
        pipe.display(frame); time.sleep(DT)
    amb.clear_motes()

# --- Registry -----------------------------------------------------
REGISTRY = [
    ('hourglass',     hourglass,     3),
    ('wheel',         wheel,         3),
    ('ripples',       ripples,       2),
    ('quill',         quill,         3),
    ('sigil',         sigil,         2),
    ('constellation', constellation, 3),
    ('glyphs',        glyphs,        2),
    ('fire',          fire,          3),
    ('orrery',        orrery,        3),
    ('recite',        recite,        2),
    ('judgment',      judgment,      1),
]
