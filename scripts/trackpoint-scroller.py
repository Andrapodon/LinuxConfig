#!/usr/bin/env python3
import evdev
from evdev import ecodes, UInput
import time
import sys
import os
import signal

CONFIG_FILE = "/etc/trackpoint-scroller.conf"

SPEED_MAP = {
    1: 12.0,  # Very slow / high precision
    2: 9.0,
    3: 7.0,
    4: 5.0,
    5: 4.0,   # Default
    6: 3.0,
    7: 2.5,
    8: 2.0,
    9: 1.5,
    10: 1.0   # Very fast
}

current_divisor = 4.0
last_mtime = 0
target_dev = None
ui = None

def cleanup(signum=None, frame=None):
    global target_dev, ui
    if target_dev:
        try:
            target_dev.ungrab()
            print("Pointing stick ungrabbed successfully.", flush=True)
        except Exception:
            pass
        target_dev = None
    if ui:
        try:
            ui.close()
        except Exception:
            pass
        ui = None
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGHUP, cleanup)

def get_divisor():
    global current_divisor, last_mtime
    try:
        if os.path.exists(CONFIG_FILE):
            mtime = os.path.getmtime(CONFIG_FILE)
            if mtime != last_mtime:
                last_mtime = mtime
                with open(CONFIG_FILE, "r") as f:
                    content = f.read().strip()
                    val = int(content)
                    val = max(1, min(10, val))
                    current_divisor = SPEED_MAP.get(val, 4.0)
                    print(f"Updated scroll speed to {val} (divisor={current_divisor})", flush=True)
    except Exception:
        pass
    return current_divisor

def find_device():
    while True:
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
                if "serio2" in str(dev.phys):
                    return dev
            except Exception:
                pass
        time.sleep(1)

def main():
    global target_dev, ui
    while True:
        try:
            target_dev = find_device()
            print(f"Acquired pointing stick: {target_dev.name} ({target_dev.path})", flush=True)

            cap = {
                ecodes.EV_REL: [
                    ecodes.REL_WHEEL,
                    ecodes.REL_HWHEEL,
                    ecodes.REL_WHEEL_HI_RES,
                    ecodes.REL_HWHEEL_HI_RES,
                ],
                ecodes.EV_KEY: [
                    ecodes.BTN_LEFT,
                    ecodes.BTN_RIGHT,
                    ecodes.BTN_MIDDLE,
                ],
            }

            ui = UInput(cap, name="Pointing Stick Scroll Device")
            target_dev.grab()
            print("Pointing stick grabbed exclusively. 2D scrolling active!", flush=True)

            accum_y = 0.0
            accum_x = 0.0

            for event in target_dev.read_loop():
                divisor = get_divisor()
                if event.type == ecodes.EV_REL:
                    if event.code == ecodes.REL_Y:
                        accum_y -= event.value
                        ticks = int(accum_y / divisor)
                        if ticks != 0:
                            ui.write(ecodes.EV_REL, ecodes.REL_WHEEL, ticks)
                            ui.write(ecodes.EV_REL, ecodes.REL_WHEEL_HI_RES, ticks * 120)
                            ui.syn()
                            accum_y %= divisor
                    elif event.code == ecodes.REL_X:
                        accum_x += event.value
                        ticks = int(accum_x / divisor)
                        if ticks != 0:
                            ui.write(ecodes.EV_REL, ecodes.REL_HWHEEL, ticks)
                            ui.write(ecodes.EV_REL, ecodes.REL_HWHEEL_HI_RES, ticks * 120)
                            ui.syn()
                            accum_x %= divisor
                elif event.type == ecodes.EV_KEY:
                    ui.write(ecodes.EV_KEY, event.code, event.value)
                    ui.syn()

        except (Exception, KeyboardInterrupt, SystemExit) as e:
            print(f"Loop exit or signal: {e}", flush=True)
            cleanup()
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    finally:
        cleanup()
