import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import ctypes
import threading
import time
import sys

# --- Windows sleep function ---
def sleep_windows():
    ctypes.windll.powrprof.SetSuspendState(False, True, False)

# --- App ---
class SleepLimiterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sleep Limiter")
        self.root.geometry("420x360")
        self.root.resizable(False, False)

        self.target_time = None
        self.running = False

        self.setup_dark_theme()
        self.build_ui()

    def setup_dark_theme(self):
        self.root.configure(bg="#121212")
        style = ttk.Style()
        style.theme_use("default")

        style.configure("TButton",
                        background="#1f1f1f",
                        foreground="white",
                        padding=6,
                        borderwidth=0)

        style.map("TButton",
                  background=[("active", "#333333")])

        style.configure("TLabel",
                        background="#121212",
                        foreground="white")

        style.configure("TEntry",
                        fieldbackground="#1f1f1f",
                        foreground="white")

    def build_ui(self):
        ttk.Label(self.root, text="Set hard sleep limit",
                  font=("Segoe UI", 14, "bold")).pack(pady=10)

        # Time picker
        picker_frame = tk.Frame(self.root, bg="#121212")
        picker_frame.pack(pady=10)

        self.hour_var = tk.StringVar(value="00")
        self.min_var = tk.StringVar(value="00")

        ttk.Entry(picker_frame, width=5, textvariable=self.hour_var).pack(side="left")
        ttk.Label(picker_frame, text=":").pack(side="left", padx=4)
        ttk.Entry(picker_frame, width=5, textvariable=self.min_var).pack(side="left")

        ttk.Button(self.root, text="Sleep at selected time",
                   command=self.set_absolute_time).pack(pady=6)

        # Absolute buttons
        abs_frame = tk.Frame(self.root, bg="#121212")
        abs_frame.pack(pady=6)

        for t in ["00:00", "01:00", "02:00"]:
            ttk.Button(abs_frame, text=t,
                       command=lambda x=t: self.quick_absolute(x)).pack(side="left", padx=5)

        # Relative buttons
        rel_frame = tk.Frame(self.root, bg="#121212")
        rel_frame.pack(pady=10)

        ttk.Label(rel_frame, text="From now:").pack(side="left", padx=5)

        for h in [1, 2, 3]:
            ttk.Button(rel_frame, text=f"{h}h",
                       command=lambda x=h: self.relative_hours(x)).pack(side="left", padx=5)

        self.status_label = ttk.Label(self.root,
                                      text="No sleep scheduled",
                                      font=("Segoe UI", 11))
        self.status_label.pack(pady=20)

    def set_absolute_time(self):
        try:
            hour = int(self.hour_var.get())
            minute = int(self.min_var.get())
            now = datetime.now()
            target = now.replace(hour=hour, minute=minute, second=0)

            if target <= now:
                target += timedelta(days=1)

            self.start_timer(target)
        except ValueError:
            self.status_label.config(text="Invalid time")

    def quick_absolute(self, time_str):
        hour, minute = map(int, time_str.split(":"))
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0)
        if target <= now:
            target += timedelta(days=1)
        self.start_timer(target)

    def relative_hours(self, hours):
        target = datetime.now() + timedelta(hours=hours)
        self.start_timer(target)

    def start_timer(self, target):
        self.target_time = target
        self.running = True
        self.update_countdown()

    def update_countdown(self):
        if not self.running:
            return

        remaining = self.target_time - datetime.now()
        seconds = int(remaining.total_seconds())

        if seconds <= 0:
            self.status_label.config(text="Sleeping now…")
            self.root.update()
            time.sleep(0.5)
            sleep_windows()
            sys.exit()

        hrs, rem = divmod(seconds, 3600)
        mins, secs = divmod(rem, 60)

        self.status_label.config(
            text=f"Sleeping in {hrs:02d}:{mins:02d}:{secs:02d}"
        )

        self.root.after(1000, self.update_countdown)


# --- Run ---
if __name__ == "__main__":
    root = tk.Tk()
    app = SleepLimiterApp(root)
    root.mainloop()
