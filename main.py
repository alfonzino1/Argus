"""
Main entry point for Real-Time Vision System.
Usage: python main.py [--config path/to/config.yaml] [--dashboard]
"""
import sys
import logging
import argparse
import threading
import queue
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2
from src.camera.capture import CameraStream
from src.models.detector import YOLODetector
from src.models.tracker import Tracker
from src.processing.pipeline import Pipeline
from src.processing.events import EventManager
from src.utils.config import load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


def create_frame_source(source_cfg: dict):
    """Factory for frame source based on config."""
    source_type = source_cfg.get("type", "video")
    if source_type == "camera":
        cam_config = {
            "width": source_cfg.get("width", 1280),
            "height": source_cfg.get("height", 720),
            "fps": source_cfg.get("fps", 30),
            "backend": source_cfg.get("backend", "CAP_ANY"),
            "reconnect_attempts": source_cfg.get("reconnect_attempts", 5),
            "reconnect_delay": source_cfg.get("reconnect_delay", 2.0),
        }
        camera = CameraStream(source=source_cfg.get("camera_index", 0), config=cam_config)
        if not camera.start():
            raise RuntimeError("Failed to start camera.")
        return camera
    else:
        video_path = source_cfg.get("video_path", "test_video.avi")
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")
        class VideoFileSource:
            def __init__(self, cap):
                self.cap = cap
            def read(self):
                ret, frame = self.cap.read()
                return ret, frame
            def stop(self):
                self.cap.release()
        return VideoFileSource(cap)


def run_dashboard(frame_q, event_q, port):
    """Start FastAPI dashboard in a thread."""
    from src.dashboard.server import app, set_queues
    import uvicorn
    set_queues(frame_q, event_q)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def main(config_path: str = "configs/default.yaml", start_dashboard: bool = False):
    logger.info(f"Loading config from {config_path}")
    config = load_config(config_path)

    frame_source = create_frame_source(config["source"])

    detector = YOLODetector(config=config["detector"])
    detector.load_model()
    detector.warmup()

    tracker = None
    tracker_cfg = config.get("tracker", {})
    if tracker_cfg.get("type") == "iou":
        tracker = Tracker(
            max_lost_frames=tracker_cfg.get("max_lost_frames", 30),
            iou_threshold=tracker_cfg.get("iou_threshold", 0.3)
        )
        logger.info("IOU tracker enabled.")
    elif tracker_cfg.get("type") == "bytetrack":
        logger.warning("ByteTrack not implemented, skipping tracker.")
        tracker = None

    event_mgr = None
    if "events" in config:
        event_mgr = EventManager(config["events"])
        logger.info("EventManager enabled.")

    # Shared queues for dashboard
    frame_queue = queue.Queue(maxsize=10)
    event_queue = queue.Queue(maxsize=100)

    if start_dashboard:
        dashboard_thread = threading.Thread(
            target=run_dashboard,
            args=(frame_queue, event_queue, 5050),
            daemon=True
        )
        dashboard_thread.start()
        logger.info("Dashboard started at http://localhost:5050")

    pipeline = Pipeline(
        frame_source,
        detector,
        tracker=tracker,
        event_manager=event_mgr,
        config=config.get("pipeline", {}),
        frame_queue=frame_queue,
        event_queue=event_queue
    )

    try:
        pipeline.run()
    except Exception as e:
        logger.exception(f"Pipeline error: {e}")
    finally:
        pipeline.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real-Time Vision System")
    parser.add_argument("--config", type=str, default="configs/default.yaml",
                        help="Path to YAML config file")
    parser.add_argument("--dashboard", action="store_true",
                        help="Start web dashboard on port 8000")
    args = parser.parse_args()
    main(args.config, args.dashboard)