#!/bin/bash
# ASUS TUF FX505GE Keyboard RGB Controller — Installer
# Tested on Pop!_OS 24.04 LTS (COSMIC), kernel 7.x

set -e

USERNAME=$(whoami)

echo "========================================"
echo " ASUS TUF Keyboard RGB Controller Setup"
echo "========================================"
echo ""

# 1. Check kernel module
echo "► Checking asus-nb-wmi kernel module..."
if lsmod | grep -q asus_nb_wmi; then
    echo "  ✓ asus-nb-wmi is loaded"
else
    echo "  Loading asus-nb-wmi..."
    sudo modprobe asus-nb-wmi
fi

# 2. Check sysfs path exists
RGB_PATH="/sys/devices/platform/asus-nb-wmi/leds/asus::kbd_backlight/kbd_rgb_mode"
if [ ! -e "$RGB_PATH" ]; then
    echo ""
    echo "  ✗ RGB sysfs path not found."
    echo "    Your laptop may use a different interface."
    echo "    Check: ls /sys/devices/platform/asus-nb-wmi/leds/"
    exit 1
fi
echo "  ✓ RGB sysfs path found"

# 3. Install Python GTK dependency
echo ""
echo "► Installing dependencies..."
sudo apt install -y python3-gi gir1.2-gtk-3.0

# 4. Copy app to /opt
echo ""
echo "► Installing app to /opt/asus-rgb/..."
sudo mkdir -p /opt/asus-rgb
sudo cp asus_rgb.py /opt/asus-rgb/
sudo chmod +x /opt/asus-rgb/asus_rgb.py

# 5. Sudoers rule — allow passwordless tee for sysfs writes
echo ""
echo "► Setting up sudoers rule..."
sudo rm -f /etc/sudoers.d/asus-rgb
{
    echo "# ASUS TUF keyboard RGB — allow tee to sysfs without password"
    echo "$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/tee"
    echo "$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/systemctl daemon-reload"
    echo "$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/systemctl enable asus-kbd-rgb.service"
} | sudo tee /etc/sudoers.d/asus-rgb > /dev/null
sudo chmod 440 /etc/sudoers.d/asus-rgb

if sudo visudo -c -f /etc/sudoers.d/asus-rgb &>/dev/null; then
    echo "  ✓ Sudoers rule installed"
else
    echo "  ✗ Sudoers syntax error — removing"
    sudo rm /etc/sudoers.d/asus-rgb
    exit 1
fi

# 6. Desktop launcher
echo ""
echo "► Installing desktop launcher..."
cat > /tmp/asus-rgb.desktop << EOF
[Desktop Entry]
Name=ASUS Keyboard RGB
Comment=Control ASUS TUF FX505GE keyboard backlight color and effects
Exec=python3 /opt/asus-rgb/asus_rgb.py
Icon=asus-rgb
Terminal=false
Type=Application
Categories=System;HardwareSettings;
EOF
sudo cp /tmp/asus-rgb.desktop /usr/share/applications/
sudo update-desktop-database 2>/dev/null || true

echo ""
echo "========================================"
echo " Installation complete!"
echo "========================================"
echo ""
echo "  Launch from app menu: search 'ASUS Keyboard RGB'"
echo "  Or run: python3 /opt/asus-rgb/asus_rgb.py"
echo ""
echo "  Use 'Apply & Save' in the app to make your"
echo "  color persist automatically after every reboot."
echo ""
