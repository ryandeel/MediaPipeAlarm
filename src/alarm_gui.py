"""
Simple window for setting the alarm.

Run:  python src/alarm_gui.py
      Any alarm_app.py flags are passed through, e.g.
      python src/alarm_gui.py --challenge pushups --log results.csv --participant avery

Type a time (or click a quick-pick button), press "Set alarm", and leave the window open.
When the time comes, the normal alarm from alarm_app.py runs (sound + camera + random
pose/action) and the camera video shows up inside this same window, after a short
loading screen while the pose model and camera start up. While it's ringing, Esc stops
the alarm and the X button stops it and closes the window.

Keyboard:
    F11              full screen on/off (starts in full screen)
    Esc              stop a ringing alarm, otherwise leave full screen
    Ctrl + / Ctrl -  bigger / smaller text,  Ctrl 0 resets it
    Tab / Shift+Tab  move between controls, Enter or Space presses the focused button

This file only *uses* alarm_app.py, it doesn't change it, so the challenge logic stays
in one place. alarm_app.main() runs in a background thread so this window stays
responsive (and can animate the loading screen) while it loads the model and camera.
alarm_app.py shows video with cv.imshow / cv.waitKey; while the alarm is ringing we
temporarily swap those two for versions that hand frames to this window instead.
Don't add GUI-only command-line flags: all flags get passed to alarm_app.py, which
rejects ones it doesn't know.

Action pictures: alarm_app picks its challenge in a local variable the GUI can't see, so
the GUI picks the challenge itself and hands it over with --challenge. That lets it show
the matching picture from ACTION_IMAGES in the top-right corner of the video, overlapping
it like the pose pictures do, so the video keeps its full size.
"""

import os
import sys
import time
import random
import datetime
import threading
import tkinter as tk
import tkinter.font as tkfont

import cv2 as cv
from PIL import Image, ImageTk

import alarm_app
from utils import overlay_corner

# ---------------- look ----------------
# all text colors are at least 4.5:1 contrast against the background they sit on
BG = "#15171c"          # window background
CARD = "#1f232b"        # panel behind the controls
FIELD = "#2a2f3a"       # text box / quick-pick buttons
FIELD_HOVER = "#363c4a"
TEXT = "#eef0f4"
MUTED = "#a3aab8"
DISABLED = "#6b7282"    # disabled controls (exempt from contrast rules, still readable)
ACCENT = "#ff8a3d"      # sunrise orange
ACCENT_HOVER = "#ff9f5e"
FOCUS = "#7cc4ff"       # keyboard focus outline, distinct from the orange
DANGER = "#ff6b78"
DANGER_BG = "#d7263d"
DANGER_BG_DIM = "#a81d30"
SUCCESS = "#3ddc84"

FAMILY = "Segoe UI"
# name -> (family, base size, weight); sizes get multiplied by the text-size setting
FONTS = {
    "title": (FAMILY, 10, "bold"),
    "clock": (FAMILY + " Light", 60, "normal"),
    "date": (FAMILY, 13, "normal"),
    "label": (FAMILY, 12, "normal"),
    "entry": (FAMILY, 22, "normal"),
    "pick": (FAMILY, 11, "normal"),
    "hint": (FAMILY, 10, "normal"),
    "button": (FAMILY, 13, "bold"),
    "status": (FAMILY, 13, "normal"),
    "banner": (FAMILY, 26, "bold"),
    "footer": (FAMILY, 10, "normal"),
}
TEXT_SCALES = [0.8, 0.9, 1.0, 1.15, 1.3, 1.5, 1.75, 2.0]

QUICK_PICKS = ["10s", "1m", "5m", "30m", "7:00am"]
TITLE = "Resisting Alarm Clock"

# challenge name (lowercase enum name, same as --challenge) -> picture overlaid on the video's
# top-right corner.
# Paths are relative to the project root (the folder that holds src/ and models/).
# Poses are left out on purpose: their pictures are set in poses.py (POSES[...].image) and
# alarm_app draws them in the corner of the video, so listing them here would show them twice.
# To add one: put the file in images/ and add a line whose key is the lowercase Action name.
ACTION_IMAGES = {
    "jumping_jacks": "images/jumping_jack.jpg",
    "pushups": "images/pushup.webp",
    "squats": "images/squat.jpg"
}
ACTION_IMAGE_SIZE = 200     # longest side in pixels, same box as pose pictures


def fmt_time(dt, seconds=True):
    """7:05:09 PM style, without the leading zero on the hour"""
    return dt.strftime("%I:%M:%S %p" if seconds else "%I:%M %p").lstrip("0")


def make_button(parent, text, command, font, bg, fg=TEXT, hover=None):
    """flat button with a hover color, a visible keyboard-focus outline, and Enter to press"""
    btn = tk.Button(parent, text=text, command=command, bg=bg, fg=fg, font=font,
                    activebackground=hover or bg, activeforeground=fg,
                    disabledforeground=DISABLED, relief="flat", bd=0, cursor="hand2",
                    padx=14, pady=7, highlightthickness=3, highlightcolor=FOCUS,
                    highlightbackground=parent["bg"], takefocus=True)
    btn.normal_bg = bg
    btn.bind("<Enter>", lambda e: btn["state"] == "normal" and btn.config(bg=hover or bg))
    btn.bind("<Leave>", lambda e: btn.config(bg=btn.normal_bg))
    btn.bind("<Return>", lambda e: btn.invoke())  # Space already works on Tk buttons
    return btn


class AlarmWindow:
    def __init__(self, root):
        self.root = root
        self.alarm_dt = None
        self.text_scale_i = TEXT_SCALES.index(1.0)
        self.fonts = {name: tkfont.Font(root, family=f, size=s, weight=w)
                      for name, (f, s, w) in FONTS.items()}
        F = self.fonts

        root.title(TITLE)
        root.configure(bg=BG)
        root.minsize(520, 600)

        # everything lives in this frame, which stays centered in the window / screen
        self.content = tk.Frame(root, bg=BG)
        self.content.pack(expand=True)

        # ---- clock ----
        tk.Label(self.content, text="RESISTING ALARM CLOCK", bg=BG, fg=MUTED,
                 font=F["title"]).pack(pady=(18, 0))
        self.clock_label = tk.Label(self.content, bg=BG, fg=TEXT, font=F["clock"])
        self.clock_label.pack(padx=30)
        self.date_label = tk.Label(self.content, bg=BG, fg=MUTED, font=F["date"])
        self.date_label.pack(pady=(0, 14))

        # ---- controls card ----
        self.card = tk.Frame(self.content, bg=CARD, padx=22, pady=18)
        self.card.pack(padx=24, pady=(0, 10), fill="x")

        tk.Label(self.card, text="Wake me at / in", bg=CARD, fg=MUTED,
                 font=F["label"]).pack(anchor="w")

        entry_border = tk.Frame(self.card, bg=FIELD, highlightthickness=3,
                                highlightbackground=FIELD, highlightcolor=FOCUS)
        entry_border.pack(fill="x", pady=(4, 10))
        self.time_entry = tk.Entry(entry_border, font=F["entry"], justify="center",
                                   bg=FIELD, fg=TEXT, insertbackground=TEXT, relief="flat",
                                   disabledbackground=FIELD, disabledforeground=DISABLED,
                                   insertwidth=3)
        self.time_entry.insert(0, "10s")
        self.time_entry.pack(fill="x", ipady=6, padx=6)
        self.time_entry.bind("<Return>", lambda e: self.set_alarm())
        # outline the box while it has keyboard focus
        self.time_entry.bind("<FocusIn>", lambda e: entry_border.config(highlightbackground=FOCUS))
        self.time_entry.bind("<FocusOut>", lambda e: entry_border.config(highlightbackground=FIELD))

        picks = tk.Frame(self.card, bg=CARD)
        picks.pack(fill="x")
        self.pick_buttons = []
        for text in QUICK_PICKS:
            b = make_button(picks, text, lambda t=text: self.quick_pick(t), F["pick"],
                            bg=FIELD, hover=FIELD_HOVER)
            b.config(padx=8, pady=3)
            b.pack(side="left", expand=True, fill="x", padx=2)
            self.pick_buttons.append(b)

        tk.Label(self.card, text="also works: 6pm, 7:30, 1h30m, 45s", bg=CARD, fg=MUTED,
                 font=F["hint"]).pack(pady=(6, 12))

        buttons = tk.Frame(self.card, bg=CARD)
        buttons.pack(fill="x")
        self.set_button = make_button(buttons, "Set alarm", self.set_alarm, F["button"],
                                      bg=ACCENT, fg="#1a1a1a", hover=ACCENT_HOVER)
        self.set_button.pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.cancel_button = make_button(buttons, "Cancel", self.cancel_alarm, F["button"],
                                         bg=FIELD, hover=FIELD_HOVER)
        self.cancel_button.pack(side="left", expand=True, fill="x", padx=(5, 0))
        self.cancel_button.config(state="disabled", takefocus=False)

        # ---- status ----
        self.status_label = tk.Label(self.content, text="No alarm set", bg=BG, fg=MUTED,
                                     font=F["status"], wraplength=700)
        self.status_label.pack(padx=24, pady=(4, 10))

        # ---- ringing view (hidden until the alarm goes off) ----
        self.banner = tk.Label(self.content, text="WAKE UP!", bg=DANGER_BG, fg="white",
                               font=F["banner"], pady=6)
        self.action_overlay = None  # how-to picture for actions, drawn onto the video
        self.video_frame = tk.Frame(self.content, bg="black", padx=3, pady=3)
        self.video_label = tk.Label(self.video_frame, bg="black")
        # loading screen shown in the video's place until the first camera frame arrives
        self.loading_canvas = tk.Canvas(self.video_frame, bg="black", highlightthickness=0)

        # ---- keyboard help, always at the bottom ----
        self.footer = tk.Label(root, bg=BG, fg=MUTED, font=F["footer"],
                               text="F11  full screen    ·    Esc  stop alarm    ·    Ctrl +/−  text size"
                                    "    ·    Tab  move    ·    Enter  press")
        self.footer.pack(side="bottom", pady=10)

        self.ringing = False
        self.stop_requested = False  # Esc pressed or window closed while ringing
        self.closing = False
        self.worker = None           # thread running alarm_app.main()
        self.latest_frame = None     # newest RGB frame from the worker, not yet displayed
        self.got_first_frame = False
        self.loading_stage = ""
        self.spin_angle = 0
        root.bind("<Escape>", lambda e: self.on_escape())
        root.bind("<F11>", lambda e: self.set_fullscreen(not self.is_fullscreen()))
        for key in ("<Control-plus>", "<Control-equal>", "<Control-KP_Add>"):
            root.bind(key, lambda e: self.change_text_size(+1))
        for key in ("<Control-minus>", "<Control-KP_Subtract>"):
            root.bind(key, lambda e: self.change_text_size(-1))
        root.bind("<Control-0>", lambda e: self.change_text_size(0))
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.set_fullscreen(True)
        self.time_entry.focus_set()
        self.time_entry.select_range(0, "end")  # so typing replaces the example time
        self.tick()

    # ---------------- full screen / text size ----------------
    def is_fullscreen(self):
        return bool(self.root.attributes("-fullscreen"))

    def set_fullscreen(self, on):
        self.root.attributes("-fullscreen", on)

    def change_text_size(self, step):
        if step == 0:
            self.text_scale_i = TEXT_SCALES.index(1.0)
        else:
            self.text_scale_i = max(0, min(len(TEXT_SCALES) - 1, self.text_scale_i + step))
        scale = TEXT_SCALES[self.text_scale_i]
        for name, (_family, size, _weight) in FONTS.items():
            self.fonts[name].configure(size=round(size * scale))
        self.status_label.config(wraplength=round(700 * scale))

    # ---------------- stopping / closing ----------------
    def on_escape(self):
        if self.ringing:
            self.stop_requested = True  # alarm_app sees Esc on its next frame and stops
        elif self.is_fullscreen():
            self.set_fullscreen(False)

    def on_close(self):
        if self.ringing:
            # alarm_app is still running in the background thread: tell it to stop, and
            # finish_ring() closes the window once it has released the camera
            self.closing = True
            self.stop_requested = True
            self.set_status("Closing...", MUTED)
        else:
            self.root.destroy()

    # ---------------- stand-ins for cv.imshow / cv.waitKey ----------------
    # These run on the background thread, so they must not touch any Tk widgets.
    # They just hand the frame / stop flag over; poll_ring() does the drawing.
    def show_frame(self, _window_name, bgr_image):
        if self.action_overlay is not None:
            # action how-to picture, top-right over the video like pose pictures
            overlay_corner(bgr_image, self.action_overlay, alpha=0.75)
        self.latest_frame = cv.cvtColor(bgr_image, cv.COLOR_BGR2RGB)

    def wait_key(self, _delay=0):
        time.sleep(0.001)  # give the window's thread a turn
        return 27 if self.stop_requested else -1  # 27 = Esc, which alarm_app checks for

    def start_sound_hook(self):
        """alarm_app calls start_sound() right after the model loads and right before it
        opens the camera, so that's when the loading screen moves to its next step."""
        self.loading_stage = "Fetching camera"
        self.real_start_sound()

    # ---------------- video area sizing ----------------
    def fit_size(self, w, h):
        """largest (w, h) with this shape that fits in the space the other widgets leave"""
        other_h = self.content.winfo_reqheight() - self.video_frame.winfo_reqheight()
        max_w = self.root.winfo_width() - 60
        max_h = self.root.winfo_height() - other_h - self.footer.winfo_reqheight() - 50
        fit = min(max_w / w, max_h / h)
        if fit <= 0:
            return w, h
        return max(1, int(w * fit)), max(1, int(h * fit))

    def draw_frame(self, rgb):
        img = Image.fromarray(rgb)
        size = self.fit_size(img.width, img.height)
        if abs(size[0] - img.width) > 2:
            img = img.resize(size)
        photo = ImageTk.PhotoImage(img)
        self.video_label.config(image=photo)
        self.video_label.image = photo  # keep a reference or tkinter drops the image

    def draw_loading(self):
        """spinner + current step, drawn where the video will appear"""
        c = self.loading_canvas
        w, h = self.fit_size(640, 480)  # same size the video will be
        c.config(width=w, height=h)
        c.delete("all")
        cx, cy = w // 2, h // 2 - 30
        r = max(20, min(w, h) // 10)
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=FIELD, width=8)
        c.create_arc(cx - r, cy - r, cx + r, cy + r, start=self.spin_angle, extent=100,
                     style="arc", outline=ACCENT, width=8)
        dots = "." * (1 + (self.spin_angle // 120) % 3)
        c.create_text(cx, cy + r + 40, text=f"{self.loading_stage}{dots}", fill=TEXT,
                      font=self.fonts["banner"])
        steps = "Step 1 of 2" if self.loading_stage.startswith("Loading") else "Step 2 of 2"
        c.create_text(cx, cy + r + 85, text=steps, fill=MUTED, font=self.fonts["status"])
        self.spin_angle = (self.spin_angle - 12) % 360

    # ---------------- setting the alarm ----------------
    def set_status(self, text, color=MUTED, announce=False):
        """announce=True also puts the message in the window title, which screen readers
        (e.g. Narrator) read out; Tk widgets themselves are mostly invisible to them"""
        self.status_label.config(text=text, fg=color)
        if announce:
            self.root.title(f"{TITLE} - {text.lstrip(chr(0x2714) + chr(0x23F0) + ' ')}")

    def set_controls_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.set_button.config(state=state, bg=ACCENT if enabled else FIELD, takefocus=enabled)
        self.set_button.normal_bg = ACCENT if enabled else FIELD
        self.time_entry.config(state=state)
        for b in self.pick_buttons:
            b.config(state=state, takefocus=enabled)
        self.cancel_button.config(state="disabled" if enabled else "normal",
                                  takefocus=not enabled)
        # keep keyboard focus on something usable
        (self.time_entry if enabled else self.cancel_button).focus_set()

    def quick_pick(self, text):
        self.time_entry.delete(0, "end")
        self.time_entry.insert(0, text)
        self.set_alarm()

    def set_alarm(self):
        try:
            self.alarm_dt = alarm_app.parse_alarm(self.time_entry.get())
        except ValueError as e:
            self.set_status(f"Error: {e}", DANGER, announce=True)
            return
        self.set_controls_enabled(False)
        self.update_countdown(datetime.datetime.now())
        self.root.title(f"{TITLE} - alarm set for {fmt_time(self.alarm_dt, seconds=False)}")

    def cancel_alarm(self):
        self.alarm_dt = None
        self.set_controls_enabled(True)
        self.set_status("Alarm cancelled", announce=True)

    def update_countdown(self, now):
        left = int((self.alarm_dt - now).total_seconds()) + 1
        h, rem = divmod(left, 3600)
        m, s = divmod(rem, 60)
        left_str = f"{h}h {m:02d}m {s:02d}s" if h else f"{m}m {s:02d}s" if m else f"{s}s"
        self.set_status(f"⏰  Alarm set for {fmt_time(self.alarm_dt, seconds=False)}"
                        f"  ·  rings in {left_str}", ACCENT)

    def tick(self):
        """Runs twice a second: update the clock and check whether it's time to ring."""
        now = datetime.datetime.now()
        self.clock_label.config(text=fmt_time(now))
        self.date_label.config(text=now.strftime("%A, %B %d").replace(" 0", " "))

        if self.alarm_dt is not None:
            if now >= self.alarm_dt:
                self.ring()
            else:
                self.update_countdown(now)

        self.root.after(500, self.tick)

    # ---------------- challenge pictures ----------------
    def pick_challenge(self):
        """Return (challenge_name, extra_argv). Respects a --challenge the window was started with."""
        argv = sys.argv[1:]
        for i, arg in enumerate(argv):
            if arg == "--challenge" and i + 1 < len(argv):
                return argv[i + 1], []
            if arg.startswith("--challenge="):
                return arg.split("=", 1)[1], []
        # same odds as alarm_app: coin flip between pose and action, then random within
        pool = alarm_app.Pose if random.randint(0, 1) == 0 else alarm_app.Action
        name = random.choice(list(pool)).name.lower()
        return name, ["--challenge", name]

    def show_action_image(self, challenge):
        """Load the how-to picture for an action; show_frame overlays it on the video's
        top-right corner, the same way alarm_app does for poses. None if it has none."""
        self.action_overlay = None
        rel_path = ACTION_IMAGES.get(challenge.lower())
        if rel_path is None:
            return
        img = cv.imread(os.path.join(alarm_app.BASE_DIR, rel_path))
        if img is None:
            # a bad filename must never stop the alarm from being turned off
            print(f"Warning: couldn't load action image {rel_path!r}")
            return
        # fit inside the same 200x200 box as pose pictures, keeping its shape
        fit = ACTION_IMAGE_SIZE / max(img.shape[:2])
        self.action_overlay = cv.resize(img, (round(img.shape[1] * fit), round(img.shape[0] * fit)))

    # ---------------- ringing ----------------
    def blink_banner(self, on=True):
        # slow (under 1 flash per second) and between two similar reds, so it's
        # noticeable without being a photosensitivity risk
        if not self.ringing:
            return
        self.banner.config(bg=DANGER_BG if on else DANGER_BG_DIM)
        self.root.after(700, self.blink_banner, not on)

    def ring(self):
        self.alarm_dt = None
        self.ringing = True
        self.stop_requested = False

        # swap the setup view for the ringing view
        self.card.pack_forget()
        self.status_label.pack_forget()
        self.banner.pack(fill="x", padx=24, pady=(0, 8))
        self.video_frame.pack(padx=24, pady=(0, 8))
        self.status_label.pack(padx=24, pady=(0, 10))
        self.set_status("Wake up! Do the challenge on screen to turn the alarm off",
                        TEXT, announce=True)
        self.blink_banner()

        # decide the challenge here so we can show its picture (must come after video_frame is packed)
        challenge, extra_args = self.pick_challenge()
        self.show_action_image(challenge)

        # loading screen until the first camera frame arrives
        self.video_label.pack_forget()
        self.loading_canvas.pack()
        self.latest_frame = None
        self.got_first_frame = False
        self.loading_stage = "Loading pose model"

        # bring the window to the front in case it was minimized or behind other windows
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        self.root.update()
        self.root.attributes("-topmost", False)

        # Reuse alarm_app's main loop as-is: give it an alarm time of 0 seconds so it
        # rings immediately, and pass along any flags this window was started with
        # (--debug, --challenge, --log, --participant, ...), plus the challenge we picked.
        self.saved_argv = sys.argv
        sys.argv = ["alarm_app.py", "0"] + self.saved_argv[1:] + extra_args
        self.saved_imshow, self.saved_waitkey = cv.imshow, cv.waitKey
        cv.imshow, cv.waitKey = self.show_frame, self.wait_key
        self.real_start_sound = alarm_app.start_sound
        alarm_app.start_sound = self.start_sound_hook
        self.bad_flags = False

        self.worker = threading.Thread(target=self.run_alarm_app, daemon=True)
        self.worker.start()
        self.poll_ring()

    def run_alarm_app(self):
        """background thread: the whole alarm_app.main() run"""
        try:
            alarm_app.main()
        except SystemExit:
            self.bad_flags = True  # argparse rejected a flag; it printed why in the terminal
        except Exception as e:
            print(f"alarm_app stopped with an error: {e!r}")
        finally:
            alarm_app.stop_sound()  # in case it was stopped with Esc / X

    def poll_ring(self):
        """window thread, ~25 times a second while ringing: draw the newest frame or the
        loading screen, and notice when alarm_app has finished"""
        if not self.worker.is_alive():
            self.finish_ring()
            return

        frame, self.latest_frame = self.latest_frame, None
        if frame is not None:
            if not self.got_first_frame:
                self.got_first_frame = True
                self.loading_canvas.pack_forget()
                self.video_label.pack()
            self.draw_frame(frame)
        elif not self.got_first_frame:
            self.draw_loading()

        self.root.after(40, self.poll_ring)

    def finish_ring(self):
        sys.argv = self.saved_argv
        cv.imshow, cv.waitKey = self.saved_imshow, self.saved_waitkey
        alarm_app.start_sound = self.real_start_sound
        self.ringing = False
        stopped_early = self.stop_requested

        if self.closing:
            self.root.destroy()
            return

        # back to the setup view
        self.banner.pack_forget()
        self.action_overlay = None
        self.video_frame.pack_forget()
        self.loading_canvas.pack_forget()
        self.video_label.config(image="")
        self.video_label.image = None
        self.status_label.pack_forget()
        self.card.pack(padx=24, pady=(0, 10), fill="x")
        self.status_label.pack(padx=24, pady=(4, 10))

        self.cancel_alarm()
        if self.bad_flags:
            self.set_status("Error: bad command-line flag, see the terminal", DANGER,
                            announce=True)
        elif stopped_early:
            self.set_status("Alarm stopped", MUTED, announce=True)
        else:
            self.set_status("✔  Alarm off. Good morning!", SUCCESS, announce=True)


if __name__ == "__main__":
    root = tk.Tk()
    AlarmWindow(root)
    root.mainloop()