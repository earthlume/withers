"""Ambient particle systems + background generator."""
import math, random, time
from .render import (DT, VOID, SHADOW_HI, DUST, WISP, EMBER, EMBER_HI,
                     lerp, mul, screen, plot_soft, vnoise)

class Mote:
    def __init__(self, x, y):
        self.x=float(x); self.y=float(y)
        self.vx=random.uniform(-0.4,0.4); self.vy=random.uniform(-1.5,-0.7)
        self.life=random.uniform(1.4,2.4); self.age=0.0
    def step(self): self.age+=DT; self.x+=self.vx*DT; self.y+=self.vy*DT
    def alive(self): return self.age < self.life
    def render(self, frame):
        b = 1 - self.age/self.life
        plot_soft(frame, self.x, self.y, lerp(EMBER, EMBER_HI, b), b*0.85)

class Dust:
    def __init__(self):
        self.x=random.uniform(0,7.99); self.y=random.uniform(0,7.99)
        self.vx=random.uniform(-0.15,0.15); self.vy=random.uniform(-0.20,-0.03)
        self.life=random.uniform(8,16); self.age=0.0
        self.base=random.uniform(0.3,0.7)
    def step(self):
        self.age+=DT; self.x=(self.x+self.vx*DT)%8.0; self.y+=self.vy*DT
        if self.y < -0.5: self.y = 8.5
    def alive(self): return self.age < self.life
    def render(self, frame):
        fade = min(1.0, self.age/0.8, (self.life-self.age)/1.2)
        plot_soft(frame, self.x, self.y, DUST, self.base*fade)

class Wisp:
    def __init__(self):
        self.t0=time.time(); self.life=random.uniform(3.5,5.5)
        self.y0=random.uniform(1.5,6.5); self.amp=random.uniform(0.6,1.4)
        self.freq=random.uniform(0.3,0.8)
        self.vx=random.uniform(0.8,1.4) * random.choice([-1,1])
        self.x = 8.5 if self.vx < 0 else -0.5; self.y=self.y0
    def step(self):
        dt = time.time()-self.t0
        self.x = (8.5 if self.vx<0 else -0.5) + self.vx*dt
        self.y = self.y0 + self.amp*math.sin(dt*self.freq*2*math.pi)
    def alive(self):
        dt = time.time()-self.t0
        return dt < self.life and -1 < self.x < 9
    def render(self, frame):
        dt = time.time()-self.t0
        fade = min(1.0, dt/0.6, (self.life-dt)/1.0)
        plot_soft(frame, self.x, self.y, WISP, fade*0.75)
        plot_soft(frame, self.x-0.5, self.y, WISP, fade*0.3)
        plot_soft(frame, self.x+0.5, self.y, WISP, fade*0.3)

class AmbientLayer:
    """Shared ambient state across all scenes. Scenes call tick()."""
    def __init__(self):
        self.dust = [Dust() for _ in range(6)]
        self.wisps = []
        self.motes = []

    def tick(self, frame, spawn_dust=True, wisp_chance=0.003):
        for d in self.dust: d.step()
        self.dust[:] = [d for d in self.dust if d.alive()]
        while spawn_dust and len(self.dust) < 7:
            self.dust.append(Dust())
        if random.random() < wisp_chance and len(self.wisps) < 2:
            self.wisps.append(Wisp())
        for w in self.wisps: w.step()
        self.wisps[:] = [w for w in self.wisps if w.alive()]
        for m in self.motes: m.step()
        self.motes[:] = [m for m in self.motes if m.alive()]
        for d in self.dust: d.render(frame)
        for w in self.wisps: w.render(frame)
        for m in self.motes: m.render(frame)

    def spawn_mote(self, x, y): self.motes.append(Mote(x, y))
    def clear_motes(self): self.motes.clear()


def full_bg(t, strength=1.0):
    pulse = (math.sin(t * 2*math.pi / 14) + 1) / 2
    frame = []
    for r in range(8):
        grad = 1.0 - (r / 7.0) * 0.4
        for c in range(8):
            n = vnoise(c*0.4 + t*0.15, r*0.4 + t*0.08, t*0.05)
            v = (0.28 + 0.32*pulse) * grad * (0.75 + 0.3*n) * strength
            frame.append(lerp(VOID, SHADOW_HI, v))
    return frame
