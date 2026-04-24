"""Color math, render pipeline (bloom/blur/dither), drawing primitives, fonts."""
import math
from sense_hat import SenseHat

FPS = 60
DT  = 1.0 / FPS

# ---- Palette -----------------------------------------------------
BLK        = (0, 0, 0)
VOID       = (5, 2, 10)
SHADOW     = (14, 8, 26)
SHADOW_HI  = (30, 18, 50)
DUST       = (50, 42, 75)
WISP       = (60, 110, 95)
AURA_DIM   = (35, 22, 8)
AURA_MID   = (110, 75, 25)
AURA_HOT   = (180, 130, 45)
AURA_CORE  = (230, 195, 115)
INK        = (175, 135, 55)
INK_HOT    = (235, 190, 85)
GLYPH      = (70, 170, 145)
GLYPH_HOT  = (130, 220, 185)
GLASS      = (60, 45, 85)
GLASS_HI   = (115, 90, 155)
SAND       = (190, 150, 70)
SAND_HI    = (230, 200, 110)
THREAD     = (225, 200, 140)
EMBER      = (150, 50, 20)
EMBER_HI   = (220, 95, 35)
FIRE_LO    = (120, 35, 10)
FIRE_MID   = (210, 95, 25)
FIRE_HI    = (240, 180, 60)
FIRE_TOP   = (255, 230, 150)
VERDICT    = (255, 230, 150)
SIGIL_COLD = (155, 180, 230)
SIGIL_HOT  = (210, 225, 255)
ORBIT_A    = (210, 180, 100)
ORBIT_B    = (120, 170, 200)
ORBIT_C    = (200, 100, 150)

# ---- Color math --------------------------------------------------
def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return (int(a[0]+(b[0]-a[0])*t), int(a[1]+(b[1]-a[1])*t), int(a[2]+(b[2]-a[2])*t))

def mul(c, s):
    return (max(0,min(255,int(c[0]*s))), max(0,min(255,int(c[1]*s))), max(0,min(255,int(c[2]*s))))

def screen(a, b):
    return (255-((255-a[0])*(255-b[0]))//255,
            255-((255-a[1])*(255-b[1]))//255,
            255-((255-a[2])*(255-b[2]))//255)

def add_cap(a, b):
    return (min(255,a[0]+b[0]), min(255,a[1]+b[1]), min(255,a[2]+b[2]))

def luma(c): return (c[0]*2 + c[1]*3 + c[2]) // 6

# ---- Noise -------------------------------------------------------
def _hash(n):
    n = (int(n) * 15731) & 0xFFFFFFFF
    return ((n * n + n) & 0xFFFFFFFF) / 0xFFFFFFFF

def vnoise(x, y, t):
    ix, iy = int(math.floor(x)), int(math.floor(y))
    fx, fy = x - ix, y - iy
    sx = fx*fx*(3-2*fx); sy = fy*fy*(3-2*fy)
    ti = int(t*10)
    a = _hash(ix + iy*57 + ti*131)
    b = _hash(ix+1 + iy*57 + ti*131)
    c = _hash(ix + (iy+1)*57 + ti*131)
    d = _hash(ix+1 + (iy+1)*57 + ti*131)
    return (1-sx)*(1-sy)*a + sx*(1-sy)*b + (1-sx)*sy*c + sx*sy*d

# ---- Drawing primitives ------------------------------------------
def plot_soft(frame, x, y, color, intensity=1.0):
    x0 = int(math.floor(x)); y0 = int(math.floor(y))
    fx = x - x0; fy = y - y0
    for xo, yo in ((0,0),(1,0),(0,1),(1,1)):
        px = x0 + xo; py = y0 + yo
        if 0 <= px < 8 and 0 <= py < 8:
            wx = fx if xo else (1-fx); wy = fy if yo else (1-fy)
            w = wx * wy
            if w > 0.001:
                frame[py*8+px] = screen(frame[py*8+px], mul(color, w*intensity))

def draw_line(frame, x0, y0, x1, y1, color, intensity=1.0):
    steps = max(1, int(max(abs(x1-x0), abs(y1-y0)) * 3))
    for i in range(steps + 1):
        t = i / steps
        plot_soft(frame, x0 + (x1-x0)*t, y0 + (y1-y0)*t, color, intensity)

# ---- Font --------------------------------------------------------
FONT = {
 'A':["010","101","111","101","101"],'B':["110","101","110","101","110"],
 'C':["011","100","100","100","011"],'D':["110","101","101","101","110"],
 'E':["111","100","110","100","111"],'F':["111","100","110","100","100"],
 'G':["011","100","101","101","011"],'H':["101","101","111","101","101"],
 'I':["111","010","010","010","111"],'J':["001","001","001","101","110"],
 'K':["101","110","100","110","101"],'L':["100","100","100","100","111"],
 'M':["10001","11011","10101","10001","10001"],'N':["1001","1101","1011","1001","1001"],
 'O':["010","101","101","101","010"],'P':["110","101","110","100","100"],
 'Q':["010","101","101","110","011"],'R':["110","101","110","101","101"],
 'S':["011","100","010","001","110"],'T':["111","010","010","010","010"],
 'U':["101","101","101","101","011"],'V':["101","101","101","101","010"],
 'W':["10001","10001","10101","11011","10001"],'X':["101","101","010","101","101"],
 'Y':["101","101","010","010","010"],'Z':["111","001","010","100","111"],
 ' ':["00","00","00","00","00"],'.':["0","0","0","0","1"],
 ',':["0","0","0","1","1"],"'":["1","1","0","0","0"],
 '!':["1","1","1","0","1"],':':["0","1","0","1","0"],
}

def text_cols(text):
    cols = []
    for ch in text:
        g = FONT.get(ch, FONT[' '])
        for c in range(len(g[0])):
            col = [0]*8
            for r in range(5):
                if c < len(g[r]) and g[r][c] == '1': col[r+2] = 1
            cols.append(col)
        cols.append([0]*8)
    return cols

# ---- Render pipeline ---------------------------------------------
class Pipeline:
    """Holds display + temporal state. Pass to scenes; they call .display(frame)."""
    def __init__(self):
        self.sense = SenseHat()
        self.sense.set_rotation(180)
        self._prev = [BLK]*64
        self._dither_phase = 0
        self._bloom_kernel = (
            (-1,-1,0.13),(0,-1,0.21),(1,-1,0.13),
            (-1, 0,0.21),           (1, 0,0.21),
            (-1, 1,0.13),(0, 1,0.21),(1, 1,0.13),
        )

    def reset_blur(self):
        self._prev = [BLK]*64

    def _bloom(self, frame, threshold=110, strength=0.38):
        ar = [p[0] for p in frame]; ag = [p[1] for p in frame]; ab = [p[2] for p in frame]
        for i in range(64):
            L = luma(frame[i])
            if L <= threshold: continue
            intensity = min(1.0, (L - threshold) / 145.0) * strength
            r, g, b = frame[i]
            px, py = i % 8, i // 8
            for dx, dy, w in self._bloom_kernel:
                nx, ny = px+dx, py+dy
                if 0 <= nx < 8 and 0 <= ny < 8:
                    ni = ny*8 + nx; k = intensity * w
                    ar[ni] += r * k; ag[ni] += g * k; ab[ni] += b * k
        return [(min(255,int(ar[i])), min(255,int(ag[i])), min(255,int(ab[i]))) for i in range(64)]

    def _blur(self, frame, blend=0.70):
        out = [lerp(self._prev[i], frame[i], blend) for i in range(64)]
        self._prev = out
        return out

    def _dither(self, frame):
        self._dither_phase = (self._dither_phase + 1) & 3
        bayer = ((0,2),(3,1))
        out = []
        for i in range(64):
            r, g, b = frame[i]
            px, py = i % 8, i // 8
            th = bayer[py & 1][px & 1]
            if self._dither_phase > th and max(r,g,b) < 10:
                out.append((0,0,0))
            else:
                out.append(frame[i])
        return out

    def display(self, frame, do_bloom=True, do_blur=True):
        if do_bloom: frame = self._bloom(frame)
        if do_blur:  frame = self._blur(frame)
        frame = self._dither(frame)
        self.sense.set_pixels(frame)

    def clear(self):
        self.sense.clear()
