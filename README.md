# Live Sports Ticker

This project was intented to be run on a raspberry pi and a spare ultra-wide monitor that can act as a sports ticker in your home. Uses a flask web server run in kiosk mode that allows for live updates of sports scores. It is currently set to hit the ESPN public APIs every 5 minutes.

---

## Updatable Parameters

To add a new league, create a parse_{league} method and then add the league to the registry

To increase the scroll speed, update `const speed = 0.2;` in index.html to whatever you desire. Lower = slower

To increase the pause duration at the top and bottom, update `const pause = 10000;` in index.html, units are ms.

## Equipment
Raspberry PI 5 Starter Kit (power, hdmi, etc.)
Ultrawide monitor turned portrait style

## Raspberry Pi Configuration

1. Load into pi, enable ssh, ssh into it

2. Update and install required packages
```
    sudo apt update && sudo apt upgrade
    sudo apt install -y git python3-pip python3-venv curl \
                    unclutter unclutter-xfixes xcompmgr \
                    chromium-browser x11-xserver-utils
```

3. Clone this repository
```
git clone https://github.com/jackmcnulty/sports-ticker.git
cd sports-ticker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. Create the ticker service
```
sudo nano /etc/systemd/system/ticker.service
```

**Update paths as appropriate**
```
[Unit]
Description=Flask Sports Ticker
After=network-online.target
Wants=network-online.target

[Service]
User=pi
WorkingDirectory=/home/pi/sports-ticker
Environment="FLASK_APP=app.py"
Environment="FLASK_ENV=production"
ExecStart=/home/pi/sports-ticker/venv/bin/flask run --host=0.0.0.0 --port=5000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

5. Verify this has worked
```
sudo systemctl daemon-reload
sudo systemctl enable --now ticker.service
sudo systemctl status ticker.service   # confirm “Active: running”
```

6. Create the kiosk shell script 
```
touch ~/sports-ticker/kiosk.sh
chmod +x ~/sports-ticker/kiosk.sh
nano ~/sports-ticker/kiosk.sh
```

```
#!/usr/bin/env bash
#
# kiosk.sh – start full-screen Chromium with hardware accel
#

URL="http://localhost:5000"

# 1) hide cursor immediately
unclutter --idle 0 --root &   # or use unclutter-xfixes if preferred

# 2) lightweight compositor to reduce tearing
xcompmgr -c -t-5 -l-5 -r4 -o.55 &

# 3) launch Chromium in kiosk
chromium-browser --kiosk "$URL" \
  --noerrdialogs --disable-infobars --incognito \
  --password-store=basic \
  --use-gl=egl \
  --enable-gpu-rasterization \
  --enable-zero-copy \
  --force-gpu-mem-available-mb=256 \
  --disable-software-rasterizer \
  --disable-features=LowLatencyCanvas2d &

wait   # keep script alive
```

7. Autostart on desktop login (essentially system boot if desktop autologin is enabled)
```
mkdir -p ~/.config/autostart
nano ~/.config/autostart/kiosk.desktop
```

```
[Desktop Entry]
Type=Application
Name=Kiosk
Exec=/home/pi/start-kiosk.sh
```

8. Rotate the orientation of the monitor using Pi OS GUI. I couldn't figure out how to do this through the CLI

9. Save all and reboot
```
sudo reboot
```