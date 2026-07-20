"""
Main processing pipeline: capture → detection → tracking → events → visualization + dashboard queues.
"""
import logging
import time
from typing import Optional
from queue import Queue

import cv2
import numpy as np

from src.camera.capture import CameraStream
from src.models.detector import BaseDetector

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(
        self,
        frame_source,
        detector: BaseDetector,
        tracker=None,
        event_manager=None,
        config: Optional[dict] = None,
        frame_queue: Optional[Queue] = None,
        event_queue: Optional[Queue] = None,
    ):
        self.frame_source = frame_source
        self.detector = detector
        self.tracker = tracker
        self.event_manager = event_manager
        self.config = config or {}
        self.window_name = self.config.get("window_name", "Real-Time Vision System")
        self.show_fps = self.config.get("show_fps", False)
        self.is_running = False
        self.frame_queue = frame_queue
        self.event_queue = event_queue

        self.class_names = [
            "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
            "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
            "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
            "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
            "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
            "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
            "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
            "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
            "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator",
            "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
        ]

        self.static_overlay = None

    def _draw_static_elements(self, frame_shape):
        if self.static_overlay is not None and self.static_overlay.shape[:2] == frame_shape[:2]:
            return self.static_overlay.copy()
        overlay = np.zeros(frame_shape, dtype=np.uint8)
        if self.event_manager:
            for line in (self.event_manager.lines or []):
                start = tuple(line['start'])
                end = tuple(line['end'])
                cv2.line(overlay, start, end, (255, 0, 0), 2)
                cv2.putText(overlay, line.get('name', ''), (start[0]+5, start[1]-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            for zone in (self.event_manager.zones or []):
                pts = np.array([zone['points']], dtype=np.int32)
                cv2.polylines(overlay, pts, isClosed=True, color=(0, 0, 255), thickness=2)
                cv2.putText(overlay, zone.get('name', ''), tuple(zone['points'][0]),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        self.static_overlay = overlay
        return overlay.copy()

    def _draw_overlay(self, frame: np.ndarray, tracks: list) -> np.ndarray:
        static = self._draw_static_elements(frame.shape)
        frame = cv2.addWeighted(frame, 1.0, static, 0.4, 0)

        for bbox, track_id in tracks:
            x1, y1, x2, y2 = bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"ID:{track_id}"
            cv2.putText(frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        if self.event_manager:
            active_now = sum(1 for t in self.event_manager.active_tracks.values() if t.get('active'))
            cv2.putText(frame, f"Active: {active_now} | Total: {self.event_manager.total_objects_count}",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        if self.show_fps:
            fps = 1.0 / (time.perf_counter() - self.last_frame_time) if hasattr(self, 'last_frame_time') else 0
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        self.last_frame_time = time.perf_counter()
        return frame

    def run(self):
        self.is_running = True
        logger.info("Pipeline started. Press 'q' to quit.")
        self.last_frame_time = time.perf_counter()
        self.static_overlay = None

        try:
            while self.is_running:
                ret, frame = self.frame_source.read()
                if not ret or frame is None or frame.size == 0:
                    if hasattr(self.frame_source, 'cap') and not isinstance(self.frame_source, CameraStream):
                        logger.info("Video ended, restarting...")
                        self.frame_source.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = self.frame_source.read()
                        if not ret or frame is None or frame.size == 0:
                            logger.warning("Cannot restart video, exiting.")
                            break
                    else:
                        logger.warning("No frame received, waiting...")
                        cv2.waitKey(100)
                        continue

                detections = self.detector.detect(frame)
                logger.debug(f"Detected {len(detections)} objects")

                tracks = []
                if self.tracker:
                    tracks = self.tracker.update(detections)
                    logger.debug(f"Tracked {len(tracks)} tracks")

                if self.event_manager:
                    self.event_manager.update(tracks)
                    tracks = self.event_manager.get_active_bboxes_with_ids()

                # Отрисовка ДО отправки в очередь
                frame = self._draw_overlay(frame, tracks)

                # Отправка кадра в дашборд (уже с маркерами)
                if self.frame_queue and not self.frame_queue.full():
                    try:
                        self.frame_queue.put_nowait(frame.copy())
                        logger.debug("Frame pushed to dashboard queue")
                    except Exception as e:
                        logger.warning(f"Failed to push frame: {e}")

                # Отправка событий в дашборд (с читаемыми сообщениями)
                if self.event_queue and self.event_manager and self.event_manager.events_this_frame:
                    for ev in self.event_manager.events_this_frame:
                        if not self.event_queue.full():
                            try:
                                ev_type = ev.get('type', 'info')
                                if ev_type == 'line_crossed':
                                    msg = f"Object {ev['track_id']} crossed line '{ev['line']}'"
                                elif ev_type == 'zone_enter':
                                    msg = f"Object {ev['track_id']} entered zone '{ev['zone']}'"
                                elif ev_type == 'zone_exit':
                                    msg = f"Object {ev['track_id']} exited zone '{ev['zone']}'"
                                else:
                                    msg = str(ev)
                                self.event_queue.put_nowait({
                                    "message": msg,
                                    "event_type": ev_type,
                                    "timestamp": time.time()
                                })
                                logger.debug("Event pushed to dashboard queue")
                            except Exception as e:
                                logger.warning(f"Failed to push event: {e}")

                cv2.imshow(self.window_name, frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break

        except KeyboardInterrupt:
            logger.info("Interrupted by user.")
        except Exception as e:
            logger.exception(f"Pipeline error: {e}")
        finally:
            self.stop()

    def stop(self):
        self.is_running = False
        if hasattr(self.frame_source, 'stop'):
            self.frame_source.stop()
        elif hasattr(self.frame_source, 'release'):
            self.frame_source.release()
        cv2.destroyAllWindows()
        logger.info("Pipeline stopped.")