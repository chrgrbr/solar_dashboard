# ☀️ Kostal Solar Dashboard

E-paper display for Kostal Solar Portal data on Raspberry Pi with Waveshare 2.7" display.

![Display](https://img.shields.io/badge/Display-264x176-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- ✅ **4 Screens**: Realtime, Daily, Monthly, Timeline
- ✅ **Physical Buttons**: Switch screens with HAT buttons
- ✅ **Auto-refresh**: Data updates every 15 minutes
- ✅ **Smart Caching**: Minimizes API calls
- ✅ **German UI**: Proper äöü and Unicode support
- ✅ **Low Power**: E-ink only uses power during refresh

---

## 📁 Project Structure

```
solar-dashboard/
├── .env                      # Your credentials (create from .env.example)
├── requirements.txt          # Python dependencies
├── auth.py                   # Authentication module
├── solar_data.py             # Data fetching module
├── epaper_screens.py         # Screen generation module
├── main.py                   # Main controller
├── README.md                 # This file
└── tmp/                      # Cache directory (auto-created)
    ├── solar_display_data.json
    └── bearer_token.txt
```

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone <your-repo>
cd solar-dashboard

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Credentials

```bash
# Create .env file
nano .env
```

Set:
```bash
KOSTAL_USERNAME=your.email@example.com
KOSTAL_PASSWORD=your_password
KOSTAL_PLANT_ID=your_plant_id
```

### 3. Install Fonts

**On Mac (for development):**
```bash
brew install --cask font-dejavu
```

**On Raspberry Pi:**
```bash
sudo apt-get update
sudo apt-get install fonts-dejavu fonts-dejavu-core
```

### 4. Test on Mac (Mock Mode)

```bash
# Test data fetching
python3 solar_data.py

# Test screen generation
python3 epaper_screens.py

# Run dashboard in mock mode (saves images to ./tmp/)
python3 main.py --mock
```

### 5. Deploy to Raspberry Pi

**Setup Pi**
```bash
sudo apt update && sudo apt upgrade -y

# Enable SPI (for e-ink)
sudo raspi-config nonint do_spi 0
# If that doesn't work (check with "lsmod | grep spi_")
# sudo raspi-config
# Go to: Interface Options → SPI → Yes → Finish → Reboot

# Install all dependencies (PiOS Bookworm)
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-pil \
    python3-numpy \
    python3-rpi.gpio \
    python3-spidev  \
    python3-setuptools \
    python3-wheel \  git \
    fonts-dejavu \
    fonts-dejavu-core \
    chromium \
    chromium-driver \
    liblgpio-dev \
    liblgpio1 \
    swig
```
**Setup venv**
```bash
#Create Venv
cd ~
pyhon -m venv venv
source venv/bin/activate
python -m pip install -U pip setuptools wheel
```

**Setup Waveshare Display**
```bash
#Install system dependencies
sudo apt-get install python3-pip python3-pil python3-numpy
sudo pip3 install RPi.GPIO spidev

# Clone Waveshare library
cd ~
git clone https://github.com/waveshare/e-Paper
cd e-Paper/RaspberryPi_JetsonNano/python
sudo pip3 install . --no-deps
```

**Clone Project and configure .env**
```bash
cd ~
git clone https://github.com/chrgrbr/solar_dashboard.git
cd solar_dashboard

#Install requirements
pip install -r requirements.txt

#Configure Env if not already done
#eg with nano
cp .env.example .env
nano .env


```


---
## 🎮 Usage

### Button Functions

| Button | Function |
|--------|----------|
| **Button 1** | Show Realtime (current W) |
| **Button 2** | Show Daily Stats (today's kWh) |
| **Button 3** | Show Monthly Stats (30-day kWh) |
| **Button 4** | Show Timeline Graph |
| **Button 1 + 4** | **Shutdown** (clear display & power off Pi) |

### Mock Mode (Testing without Hardware)

```bash
python3 main.py --mock
```

Commands:
- `1` - Show realtime
- `2` - Show daily  
- `3` - Show monthly
- `4` - timeline
- `q` - Quit

Images saved to `./tmp/current_display_*.png`

---

## 🖼️ Screens

### Screen 1: Realtime (Echtzeit)
Shows current power in Watts

### Screen 2: Daily (Heute)
Today's generation and consumption breakdown

### Screen 3: Monthly (30 Tage)
30-day totals with daily average

### Screen 4: Timeline (Tagesverlauf)
Power curve graph showing solar generation over the day

---

## ⚙️ Configuration

### Auto-refresh Settings

Edit `main.py`:
```python
DATA_CACHE_MINUTES = 15        # Refresh data every 15 min
SCREEN_TIMEOUT_MINUTES = 30    # Return to screen 1 after 30 min
```

### GPIO Pin Mapping

Default (Waveshare 2.7" HAT):
```python
BUTTON_1_PIN = 5   # KEY1
BUTTON_2_PIN = 6   # KEY2
BUTTON_3_PIN = 13  # KEY3
BUTTON_4_PIN = 19  # KEY4
```

Check [Waveshare Wiki](https://www.waveshare.com/wiki/2.7inch_e-Paper_HAT) for your model.

---

## 🔄 Automation & Service Setup

### 1. Systemd Service (Auto-start on Boot)

Create `/etc/systemd/system/solar-dashboard.service`:

```ini
[Unit]
Description=Kostal Solar Dashboard
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/solar_dashboard
Environment="PATH=/home/pi/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/pi/venv/bin/python3 -u /home/pi/solar_dashboard/main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable solar-dashboard.service
sudo systemctl start solar-dashboard.service
```

### 2. Configure Shutdown Permission

Allow button combo (1+4) to power off the Pi:

```bash
sudo visudo
```

Add at the end (replace `pi` with your username):
```
pi ALL=(ALL) NOPASSWD: /bin/systemctl poweroff, /bin/systemctl reboot
```

### 3. View Logs

```bash
# Live logs (follow mode)
sudo journalctl -u solar-dashboard.service -f

# Last 50 lines
sudo journalctl -u solar-dashboard.service -n 50

# Check if running
sudo systemctl status solar-dashboard.service
```

### 4. Service Management

```bash
# Stop service
sudo systemctl stop solar-dashboard.service

# Restart service
sudo systemctl restart solar-dashboard.service

# Disable auto-start
sudo systemctl disable solar-dashboard.service
```

---

## 📄 License

MIT License

---

## 🙏 Credits

- [Kostal Solar Portal](https://kostal-solar-portal.com) - API
- [Waveshare](https://www.waveshare.com/wiki/2.7inch_e-Paper_HAT) - E-paper display
- [Selenium](https://www.selenium.dev/) - Web automation
- [Matplotlib](https://matplotlib.org/) - Graphs
- Claude ofc.
---

Made with ☀️ and ⚡
