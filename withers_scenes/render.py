"""Color math, render pipeline (bloom/blur/dither/quake), drawing primitives, fonts."""
import math
import numpy as np
from sense_hat import SenseHat

FPS = 60
DT  = 1.0 / FPS

# ---- Palette (unchanged) -----------------------------------------
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
_BAYER_2x2 = np.array([[0, 2], [3, 1]], dtype=np.int32)
_BAYER_8x8 = np.tile(_BAYER_2x2, (4, 4))
_BLOOM_KERNEL = np.array([[0.13, 0.21, 0.13],
                          [0.21, 0.00, 0.21],
                          [0.13, 0.21, 0.13]], dtype=np.float32)
_LUMA_W = np.array([2.0/6.0, 3.0/6.0, 1.0/6.0], dtype=np.float32)
# Grayscale weights for desaturation
_GRAY_W = np.array([0.299, 0.587, 0.114], dtype=np.float32)


class Pipeline:
    def __init__(self):
        self.sense = SenseHat()
        self.sense.set_rotation(180)
        self._prev = np.zeros((8, 8, 3), dtype=np.float32)
        self._dither_phase = 0
        self.last_frame = [(0,0,0)] * 64

    def reset_blur(self):
        self._prev[:] = 0.0

    @staticmethod
    def _to_array(frame):
        return np.asarray(frame, dtype=np.float32).reshape(8, 8, 3)

    @staticmethod
    def _bloom(arr, threshold=110.0, strength=0.38):
        L = arr @ _LUMA_W
        excess = np.maximum(L - threshold, 0.0) / 145.0
        np.minimum(excess, 1.0, out=excess)
        excess *= strength
        if not excess.any():
            return arr
        src = arr * excess[..., None]
        pad = np.zeros((10, 10, 3), dtype=np.float32)
        pad[1:9, 1:9] = src
        out = arr.copy()
        k = _BLOOM_KERNEL
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                w = k[dy + 1, dx + 1]
                if w == 0.0: continue
                out += pad[1 + dy : 9 + dy, 1 + dx : 9 + dx] * w
        np.minimum(out, 255.0, out=out)
        return out

    def _blur(self, arr, blend=0.70):
        out = self._prev + (arr - self._prev) * blend
        self._prev = out
        return out

    def _dither(self, arr):
        self._dither_phase = (self._dither_phase + 1) & 3
        max_c = arr.max(axis=-1)
        kill = (self._dither_phase > _BAYER_8x8) & (max_c < 10.0)
        arr = arr.copy()
        arr[kill] = 0.0
        return arr

    @staticmethod
    def _quake(arr, intensity):
        """Per-pixel jitter + desaturation. intensity in [0, 1].

        Quake effect: randomly swap each pixel with a neighbor (offset by 1)
        and bleed toward grayscale.
        """
        if intensity <= 0: return arr
        # Desaturate
        gray = (arr @ _GRAY_W)[..., None]  # (8,8,1)
        desat_amount = intensity * 0.45
        arr = arr * (1 - desat_amount) + gray * desat_amount
        # Jitter: for each pixel, with probability=intensity, replace with random neighbor
        h, w = 8, 8
        rng = np.random.default_rng()
        # Random offsets in {-1, 0, +1} per pixel per axis
        dy = rng.integers(-1, 2, size=(h, w))
        dx = rng.integers(-1, 2, size=(h, w))
        swap_mask = rng.random((h, w)) < intensity * 0.6  # boolean grid
        # Build index arrays
        ys, xs = np.meshgrid(np.arange(h), np.arange(w), indexing='ij')
        src_y = np.clip(ys + dy, 0, h-1)
        src_x = np.clip(xs + dx, 0, w-1)
        jittered = arr[src_y, src_x]
        arr = np.where(swap_mask[..., None], jittered, arr)
        return arr

    def display(self, frame, do_bloom=True, do_blur=True, state=None):
        arr = self._to_array(frame)
        if do_bloom: arr = self._bloom(arr)
        if do_blur:  arr = self._blur(arr)
        arr = self._dither(arr)
        # Quake overlay (AFTER everything else — most dramatic placement)
        if state is not None and state.disturbance_active:
            import time
            elapsed = time.time() - state.disturbance_t_start
            # Ramp in (0-0.3s), hold (0.3-1.2s), ramp out (1.2-1.5s)
            if elapsed < 0.3:    intensity = elapsed / 0.3
            elif elapsed < 1.2:  intensity = 1.0
            else:                intensity = max(0, 1 - (elapsed - 1.2) / 0.3)
            arr = self._quake(arr, intensity)
        np.clip(arr, 0.0, 255.0, out=arr)
        arr_u8 = arr.astype(np.uint8)
        out = [(int(r), int(g), int(b)) for r, g, b in arr_u8.reshape(64, 3)]
        self.last_frame = out
        self.sense.set_pixels(out)

    def clear(self):
        self.sense.clear()
