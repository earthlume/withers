# Withers

LED matrix animation for the Sense HAT on Withers (Pi 2B, network cabinet watchdog).

## Layout

- `withers_scenes/` — scene animation package
  - `render.py` — palette, color math, drawing primitives, render pipeline (bloom/blur/dither)
  - `ambient.py` — particle systems (dust, wisps, motes) and volumetric background
  - `scenes.py` — all scenes + registry
  - `main.py` — entry point, scene scheduler
- `.venv/` — Python venv with `--system-site-packages` (sees apt's `python3-sense-hat`)

## Run

    .venv/bin/python -m withers_scenes.main

## Service

Installed at `~/.config/systemd/user/withers-scenes.service`.

    systemctl --user restart withers-scenes   # after editing scenes
    systemctl --user status withers-scenes
    journalctl --user -u withers-scenes -f

Persistence across reboot requires `sudo loginctl enable-linger lume` (one-time).

## Scenes

Hourglass, wheel, ripples, quill, sigil, constellation, glyphs, fire, orrery, recite, judgment.
