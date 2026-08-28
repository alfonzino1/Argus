# Quick Start Guide

Get Real-Time Vision System running in under 5 minutes!

## 🚀 Fastest Way: Docker

```bash
# 1. Clone and enter directory
git clone https://github.com/yourusername/real-time-vision-system.git
cd real-time-vision-system

# 2. Build and run (uses default video file mode)
docker-compose up --build

# 3. Open browser to http://localhost:5050
```

That's it! The system will start processing the test video and display results on the dashboard.

## 💻 Local Development Setup

### Prerequisites Check
```bash
python --version  # Should be 3.10+
pip --version
```

### Installation (Linux/Mac)
```bash
# Clone repo
git clone https://github.com/yourusername/real-time-vision-system.git
cd real-time-vision-system

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run with dashboard
python main.py --dashboard
```

### Installation (Windows)
```powershell
# Clone repo
git clone https://github.com/yourusername/real-time-vision-system.git
cd real-time-vision-system

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate

# Install dependencies
pip install -r requirements.txt

# Run with dashboard
python main.py --dashboard
```

## 📹 Using Your Camera

### Option 1: Update Config
Edit `configs/default.yaml`:
```yaml
source:
  type: "camera"
  camera_index: 0  # Change to your camera ID
```

### Option 2: Command Line
```bash
# Create a custom config or modify default
python main.py --config configs/default.yaml --dashboard
```

### Find Camera Index (Linux)
```bash
ls -l /dev/video*
# Try different indices: 0, 1, 2, etc.
```

### Test Camera (Python)
```bash
python -c "import cv2; cap = cv2.VideoCapture(0); ret, frame = cap.read(); print('Camera works!' if ret else 'No camera'); cap.release()"
```

## 🎯 Common Scenarios

### Process a Video File
1. Place video in `data/videos/`
2. Edit `configs/default.yaml`:
   ```yaml
   source:
     type: "video"
     video_path: "data/videos/my_video.mp4"
   ```
3. Run: `python main.py --dashboard`

### Run Without Dashboard (Headless)
```bash
python main.py
# Or with Docker:
docker-compose run --rm vision-system python main.py
```

### Use GPU (NVIDIA)
Ensure NVIDIA Container Toolkit is installed, then:
```bash
docker-compose up --build
# GPU will be automatically used if available
```

## ⚠️ Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| "ModuleNotFoundError" | Run `pip install -r requirements.txt` |
| "Camera not found" | Check `camera_index`, test with `ls /dev/video*` |
| "Port 5050 in use" | Kill process or change port in code |
| Docker permission denied | `sudo usermod -aG docker $USER && newgrp docker` |
| No video in dashboard | Check logs: `docker-compose logs -f` |

## 📊 What You'll See

Once running:
1. **Terminal**: Processing logs, FPS, detection info
2. **Dashboard** (http://localhost:5050):
   - Live video stream with bounding boxes
   - Event log (zone entries, line crossings)
   - Real-time updates via WebSocket

## 🛑 Stopping the System

```bash
# Docker
docker-compose down

# Local
Press Ctrl+C in terminal
```

## ➡️ Next Steps

- Read full [README.md](README.md) for detailed documentation
- Customize configuration in `configs/`
- Set up zones and lines for event detection
- Deploy to production with security hardening

---

**Need help?** Check the full README or open an issue on GitHub.
