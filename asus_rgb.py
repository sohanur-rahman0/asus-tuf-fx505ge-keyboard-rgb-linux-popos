#!/usr/bin/env python3
"""
ASUS TUF FX505GE Keyboard RGB Controller
=========================================
Confirmed working on:
  - ASUS TUF FX505GE (GTX 1050 Ti, i5-8300H)
  - Pop!_OS 24.04 LTS (COSMIC desktop)
  - Kernel 7.x with asus-nb-wmi module

Sysfs interface:
  /sys/devices/platform/asus-nb-wmi/leds/asus::kbd_backlight/kbd_rgb_mode
  Format: cmd mode R G B speed
    cmd   : always 0
    mode  : 0=static, 1=breathing, 2=color_cycle
    R G B : 0-255 (standard RGB order)
    speed : 0-255 (used for breathing and color cycle)

Author: (your name here)
License: MIT
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import subprocess

RGB_MODE_PATH  = "/sys/devices/platform/asus-nb-wmi/leds/asus::kbd_backlight/kbd_rgb_mode"
RGB_STATE_PATH = "/sys/devices/platform/asus-nb-wmi/leds/asus::kbd_backlight/kbd_rgb_state"

# Standard RGB order — confirmed working on FX505GE
PRESETS = {
    "Red":    (255, 0,   0),
    "Green":  (0,   255, 0),
    "Blue":   (0,   0,   255),
    "White":  (255, 255, 255),
    "Purple": (255, 0,   255),
    "Cyan":   (0,   255, 255),
    "Yellow": (255, 255, 0),
    "Orange": (255, 128, 0),
    "Pink":   (255, 50,  128),
    "Off":    (0,   0,   0),
}

# Mode 3 (strobe) is accepted by kernel but ignored by FX505GE firmware
MODES = {
    "Static":      0,
    "Breathing":   1,
    "Color Cycle": 2,
}

class AsusRGBApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="ASUS TUF Keyboard RGB")
        self.set_default_size(420, 560)
        self.set_resizable(False)
        self.set_border_width(20)

        self.r = 255
        self.g = 255
        self.b = 255
        self.mode = 0
        self.speed = 50

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.add(main_box)

        # Title
        title = Gtk.Label()
        title.set_markup("<b>ASUS TUF FX505GE — Keyboard RGB</b>")
        title.set_halign(Gtk.Align.START)
        main_box.pack_start(title, False, False, 0)

        # Color preview bar
        self.preview = Gtk.DrawingArea()
        self.preview.set_size_request(380, 56)
        self.preview.connect("draw", self.on_draw_preview)
        main_box.pack_start(self.preview, False, False, 0)

        # Preset buttons
        preset_label = Gtk.Label()
        preset_label.set_markup("<b>Presets</b>")
        preset_label.set_halign(Gtk.Align.START)
        main_box.pack_start(preset_label, False, False, 0)

        preset_flow = Gtk.FlowBox()
        preset_flow.set_max_children_per_line(5)
        preset_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        preset_flow.set_row_spacing(6)
        preset_flow.set_column_spacing(6)

        for name, (r, g, b) in PRESETS.items():
            btn = Gtk.Button(label=name)
            btn.set_size_request(64, 32)
            brightness = r + g + b
            text_color = "black" if brightness > 380 else "white"
            css = f"button {{ background-color: rgb({r},{g},{b}); color: {text_color}; border-radius: 6px; }}"
            provider = Gtk.CssProvider()
            provider.load_from_data(css.encode())
            btn.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            btn.connect("clicked", self.on_preset_clicked, r, g, b)
            preset_flow.add(btn)

        main_box.pack_start(preset_flow, False, False, 0)

        # Custom RGB sliders
        custom_label = Gtk.Label()
        custom_label.set_markup("<b>Custom Color</b>")
        custom_label.set_halign(Gtk.Align.START)
        main_box.pack_start(custom_label, False, False, 0)

        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(10)
        self.r_scale = self._make_slider(grid, "Red",   0, self.r)
        self.g_scale = self._make_slider(grid, "Green", 1, self.g)
        self.b_scale = self._make_slider(grid, "Blue",  2, self.b)
        main_box.pack_start(grid, False, False, 0)

        # Effect mode dropdown
        mode_label = Gtk.Label()
        mode_label.set_markup("<b>Effect Mode</b>")
        mode_label.set_halign(Gtk.Align.START)
        main_box.pack_start(mode_label, False, False, 0)

        self.mode_combo = Gtk.ComboBoxText()
        for m in MODES:
            self.mode_combo.append_text(m)
        self.mode_combo.set_active(0)
        self.mode_combo.connect("changed", self.on_mode_changed)
        main_box.pack_start(self.mode_combo, False, False, 0)

        # Speed slider
        speed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        speed_lbl = Gtk.Label(label="Speed")
        speed_lbl.set_width_chars(6)
        speed_lbl.set_halign(Gtk.Align.START)
        self.speed_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 255, 1)
        self.speed_scale.set_value(self.speed)
        self.speed_scale.set_hexpand(True)
        self.speed_scale.connect("value-changed", self.on_speed_changed)
        speed_box.pack_start(speed_lbl, False, False, 0)
        speed_box.pack_start(self.speed_scale, True, True, 0)
        main_box.pack_start(speed_box, False, False, 0)

        # Action buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        apply_btn = Gtk.Button(label="Apply")
        apply_btn.set_hexpand(True)
        apply_btn.connect("clicked", self.on_apply)
        green_css = b"button { background-color: #1D9E75; color: white; border-radius: 6px; font-weight: bold; }"
        gp = Gtk.CssProvider()
        gp.load_from_data(green_css)
        apply_btn.get_style_context().add_provider(gp, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        save_btn = Gtk.Button(label="Apply & Save (persist on reboot)")
        save_btn.set_hexpand(True)
        save_btn.connect("clicked", self.on_save)

        btn_box.pack_start(apply_btn, True, True, 0)
        btn_box.pack_start(save_btn, True, True, 0)
        main_box.pack_start(btn_box, False, False, 0)

        # Status bar
        self.status = Gtk.Label(label="Ready")
        self.status.set_halign(Gtk.Align.START)
        main_box.pack_start(self.status, False, False, 0)

        self.show_all()

    def _make_slider(self, grid, label, row, value):
        lbl = Gtk.Label(label=label)
        lbl.set_halign(Gtk.Align.START)
        lbl.set_width_chars(6)
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 255, 1)
        scale.set_value(value)
        scale.set_hexpand(True)
        scale.connect("value-changed", self.on_color_changed)
        grid.attach(lbl, 0, row, 1, 1)
        grid.attach(scale, 1, row, 1, 1)
        return scale

    def on_draw_preview(self, widget, cr):
        r, g, b = self.r / 255, self.g / 255, self.b / 255
        cr.set_source_rgb(r, g, b)
        cr.rectangle(0, 0, 380, 56)
        cr.fill()
        lum = 0.299*r + 0.587*g + 0.114*b
        fg = 0 if lum > 0.5 else 1
        cr.set_source_rgb(fg, fg, fg)
        cr.select_font_face("Sans")
        cr.set_font_size(13)
        cr.move_to(10, 35)
        cr.show_text(f"Preview   R:{self.r}  G:{self.g}  B:{self.b}")

    def on_color_changed(self, scale):
        self.r = int(self.r_scale.get_value())
        self.g = int(self.g_scale.get_value())
        self.b = int(self.b_scale.get_value())
        self.preview.queue_draw()

    def on_preset_clicked(self, btn, r, g, b):
        self.r, self.g, self.b = r, g, b
        self.r_scale.set_value(r)
        self.g_scale.set_value(g)
        self.b_scale.set_value(b)
        self.preview.queue_draw()

    def on_mode_changed(self, combo):
        self.mode = MODES[combo.get_active_text()]

    def on_speed_changed(self, scale):
        self.speed = int(scale.get_value())

    def write_rgb(self):
        value = f"0 {self.mode} {self.r} {self.g} {self.b} {self.speed}"
        try:
            result = subprocess.run(
                ["sudo", "tee", RGB_MODE_PATH],
                input=value, capture_output=True, text=True
            )
            if result.returncode != 0:
                return False
            subprocess.run(
                ["sudo", "tee", RGB_STATE_PATH],
                input="0 1 1 1 1", capture_output=True, text=True
            )
            return True
        except Exception:
            return False

    def on_apply(self, btn):
        if self.write_rgb():
            mode_name = self.mode_combo.get_active_text()
            self.status.set_text(f"✓ Applied — {mode_name}  R:{self.r} G:{self.g} B:{self.b}")
        else:
            self.status.set_text("✗ Failed — check that install.sh was run")

    def on_save(self, btn):
        service = f"""[Unit]
Description=ASUS TUF Keyboard RGB persistent setting
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'echo "0 {self.mode} {self.r} {self.g} {self.b} {self.speed}" | tee {RGB_MODE_PATH}'
ExecStart=/bin/bash -c 'echo "0 1 1 1 1" | tee {RGB_STATE_PATH}'

[Install]
WantedBy=multi-user.target
"""
        try:
            subprocess.run(
                ["sudo", "tee", "/etc/systemd/system/asus-kbd-rgb.service"],
                input=service, capture_output=True, text=True
            )
            subprocess.run(["sudo", "systemctl", "daemon-reload"], capture_output=True)
            subprocess.run(["sudo", "systemctl", "enable", "asus-kbd-rgb.service"], capture_output=True)
            self.write_rgb()
            self.status.set_text("✓ Saved — will apply automatically on every boot")
        except Exception as e:
            self.status.set_text(f"✗ Save failed: {e}")

def main():
    app = AsusRGBApp()
    app.connect("destroy", Gtk.main_quit)
    Gtk.main()

if __name__ == "__main__":
    main()
