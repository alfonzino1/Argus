# Real-Time Vision System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

A professional real-time computer vision system for object detection, tracking, and event monitoring with a web-based dashboard. Built for production deployments with Docker support, comprehensive documentation, and enterprise-grade features.

## 🚀 Features

- **Real-time Object Detection**: YOLOv8 integration for fast, accurate detection
- **Multi-object Tracking**: IOU tracker (ByteTrack ready)
- **Event System**: Configurable zone entry/exit and line crossing detection
- **Web Dashboard**: Live video streaming and event logging via WebSocket
- **Camera Resilience**: Automatic reconnection on camera failure
- **Production Ready**: Docker containerization, health checks, non-root user
- **Configurable**: YAML-based configuration for all components
- **Extensible**: Modular architecture for easy customization

## 📋 Requirements

### Hardware
- CPU: Modern multi-core processor (4+ cores recommended)
- RAM: 8GB minimum, 16GB recommended
- GPU: NVIDIA GPU with CUDA support (optional, for accelerated inference)
- Camera: USB webcam, IP camera, or video file input

### Software
- Docker 20.10+ (for containerized deployment)
- Python 3.10+ (for local development)
- OpenCV-compatible camera drivers

## 🛠️ Installation

### Option 1: Docker (Recommended for Production)

**Prerequisites**: Docker and Docker Compose installed

```bash
# Clone the repository
git clone https://github.com/yourusername/real-time-vision-system.git
cd real-time-vision-system

# Build and run with Docker Compose
docker-compose up --build

# Access the dashboard at http://localhost:5050
```

**With GPU Support** (NVIDIA):
```bash
# Ensure NVIDIA Container Toolkit is installed
# Then run:
docker-compose up --build
```

**Run specific configuration**:
```bash
docker-compose run --rm vision-system python main.py --config configs/custom.yaml --dashboard
```

### Option 2: Local Development

**Prerequisites**: Python 3.10+, pip, OpenCV dependencies

```bash
# Clone the repository
git clone https://github.com/yourusername/real-time-vision-system.git
cd real-time-vision-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the system
python main.py --config configs/default.yaml --dashboard
```

**System Dependencies** (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    ffmpeg
```

## ⚙️ Configuration

All settings are configured via YAML files in the `configs/` directory.

### Example Configuration (`configs/default.yaml`)

```yaml
# Source configuration
source:
  type: "camera"          # "camera" or "video"
  camera_index: 0         # Camera device index
  width: 1280
  height: 720
  fps: 30
  reconnect_attempts: 5
  reconnect_delay: 2.0

# Detector configuration
detector:
  model_path: "yolov8n.pt"
  confidence_threshold: 0.5
  iou_threshold: 0.45
  device: null            # null = auto (CPU/CUDA)
  img_size: 640

# Tracker configuration
tracker:
  type: "iou"             # "iou" or "bytetrack"
  max_lost_frames: 30
  iou_threshold: 0.3

# Event detection
events:
  log_events: true
  lines:
    - name: "entry_line"
      start: [100, 200]
      end: [500, 200]
  zones:
    - name: "restricted_zone"
      points: [[100,100], [400,100], [400,400], [100,400]]
```

### Configuration Options

| Section | Parameter | Description | Default |
|---------|-----------|-------------|---------|
| `source` | `type` | Input source type | `"video"` |
| | `camera_index` | Camera device ID | `0` |
| | `video_path` | Path to video file | `"test_video.avi"` |
| | `width`, `height` | Frame dimensions | `1280x720` |
| | `fps` | Target FPS | `60` |
| | `reconnect_attempts` | Camera reconnection tries | `5` |
| `detector` | `model_path` | YOLO model file | `"yolov8n.pt"` |
| | `confidence_threshold` | Detection confidence | `0.5` |
| | `iou_threshold` | NMS IoU threshold | `0.45` |
| | `device` | Computing device | `null` (auto) |
| `tracker` | `type` | Tracker algorithm | `"iou"` |
| | `max_lost_frames` | Frames before losing track | `30` |
| | `iou_threshold` | Matching IoU threshold | `0.3` |

## 🚀 Usage

### Basic Run

```bash
# With default config, no dashboard
python main.py

# With custom config and dashboard
python main.py --config configs/custom.yaml --dashboard

# Dashboard available at http://localhost:5050
```

### Docker Commands

```bash
# Build and start
docker-compose up --build

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Rebuild after code changes
docker-compose up --build

# Run one-off command
docker-compose run --rm vision-system python main.py --help
```

### Dashboard Features

- **Live Video Stream**: Real-time video with detection overlays
- **Event Log**: Chronological list of zone entries, exits, and line crossings
- **WebSocket Connection**: Low-latency updates
- **Responsive UI**: Works on desktop and mobile browsers

## 📁 Project Structure

```
real-time-vision-system/
├── main.py                 # Application entry point
├── dashboard.py            # Dashboard runner (legacy)
├── requirements.txt        # Python dependencies
├── Dockerfile             # Production Docker image
├── docker-compose.yml     # Multi-container setup
├── .dockerignore          # Docker build exclusions
├── .gitignore            # Git exclusions
├── configs/
│   └── default.yaml       # Default configuration
├── src/
│   ├── __init__.py
│   ├── camera/
│   │   └── capture.py     # Camera stream handling
│   ├── models/
│   │   ├── detector.py    # YOLO detector wrapper
│   │   └── tracker.py     # Object tracking
│   ├── processing/
│   │   ├── pipeline.py    # Processing pipeline
│   │   └── events.py      # Event detection logic
│   ├── dashboard/
│   │   └── server.py      # FastAPI web server
│   └── utils/
│       └── config.py      # Configuration loader
├── tests/
│   ├── __init__.py
│   └── test_camera.py     # Unit tests
└── data/                   # (Not in repo) Videos, models
    ├── videos/
    └── models/
```

## 🔧 Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=src --cov-report=html
```

### Code Style

```bash
# Install linting tools
pip install black flake8 mypy

# Format code
black src/ main.py dashboard.py

# Lint
flake8 src/ main.py

# Type checking
mypy src/
```

### Adding Custom Models

1. Place model file in `data/models/`
2. Update `detector.model_path` in config
3. Ensure model format is compatible with Ultralytics YOLO

### Extending Event Detection

Edit `src/processing/events.py` to add custom event types:

```python
class EventManager:
    def check_custom_event(self, detections, frame):
        # Your custom logic here
        pass
```

## 🐛 Troubleshooting

### Camera Not Found
```bash
# List available cameras
ls /dev/video*

# Test camera with OpenCV
python -c "import cv2; cap = cv2.VideoCapture(0); print(cap.isOpened())"
```

### GPU Not Detected
```bash
# Check NVIDIA drivers
nvidia-smi

# Verify PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"
```

### Dashboard Connection Issues
```bash
# Check if port 5050 is in use
netstat -tlnp | grep 5050

# Try different port
python main.py --dashboard  # Edit dashboard.py to change port
```

### Docker Permission Errors
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Or run with sudo (not recommended)
sudo docker-compose up
```

## 📊 Performance Optimization

### CPU Mode
- Use smaller models: `yolov8n.pt` or `yolov8s.pt`
- Reduce input size: `img_size: 416`
- Lower FPS target in config

### GPU Mode
- Use larger models for better accuracy
- Enable TensorRT for production (future feature)
- Set `device: "cuda"` explicitly

### Multi-Camera Setup (Future)
- Run multiple instances with different configs
- Use Docker Compose to orchestrate
- Centralize dashboard (planned feature)

## 🔒 Security Considerations

### Production Deployment Checklist

- [ ] Change default ports if exposed publicly
- [ ] Add authentication to dashboard (planned)
- [ ] Use HTTPS/TLS termination (nginx example in docker-compose.yml)
- [ ] Restrict network access with firewall rules
- [ ] Keep dependencies updated
- [ ] Use secrets management for sensitive configs
- [ ] Enable container security scanning

### Current Limitations

⚠️ **Note**: The dashboard currently has no authentication. Do not expose port 5050 to untrusted networks without additional protection (firewall, VPN, or reverse proxy with auth).

## 🗺️ Roadmap

### v1.0 (Current)
- ✅ Basic detection and tracking
- ✅ Web dashboard
- ✅ Docker support
- ✅ Event detection

### v1.1 (Planned)
- [ ] ByteTrack implementation
- [ ] Dashboard authentication
- [ ] Multi-camera support
- [ ] Database integration for event storage
- [ ] REST API for configuration

### v2.0 (Future)
- [ ] Analytics and reporting
- [ ] Alert notifications (email, webhook)
- [ ] Advanced filtering and search
- [ ] Mobile app
- [ ] Cloud deployment templates

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Contribution Guidelines

- Write tests for new features
- Follow PEP 8 style guidelines
- Add docstrings to public functions
- Update documentation as needed
- Ensure Docker build still works

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics)
- [OpenCV](https://opencv.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [BoxMOT](https://github.com/mikel-brostrom/boxmot)

## 📞 Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/real-time-vision-system/issues)
- Email: your.email@example.com
- Documentation: See `docs/` directory (planned)

---

**Built with ❤️ for production computer vision deployments**
