#!/bin/bash
# ASUS TUF Keyboard RGB Controller — Uninstaller

echo "Uninstalling ASUS RGB Controller..."

sudo systemctl disable asus-kbd-rgb.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/asus-kbd-rgb.service
sudo systemctl daemon-reload 2>/dev/null || true
sudo rm -rf /opt/asus-rgb
sudo rm -f /etc/sudoers.d/asus-rgb
sudo rm -f /usr/share/applications/asus-rgb.desktop
sudo update-desktop-database 2>/dev/null || true

echo "✓ Uninstalled successfully"
