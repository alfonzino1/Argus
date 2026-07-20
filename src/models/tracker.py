"""
Simple IOU-based object tracker.
Keeps track of objects across frames using bounding box overlap.
No external dependencies beyond NumPy.
"""
import logging
import numpy as np
from typing import List, Tuple
from src.models.detector import Detection

logger = logging.getLogger(__name__)


class Tracker:
    """
    Lightweight multi-object tracker based on Intersection-over-Union (IOU).

    Parameters
    ----------
    max_lost_frames : int
        Number of frames to keep a track alive without being matched.
    iou_threshold : float
        Minimum IOU to consider a detection as matching an existing track.
    """

    def __init__(self, max_lost_frames: int = 30, iou_threshold: float = 0.3):
        self.max_lost_frames = max_lost_frames
        self.iou_threshold = iou_threshold
        self.tracks = []  # list of dict: {id, bbox, lost_frames}
        self.next_id = 1

    @staticmethod
    def _iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
        """Compute IOU between two bounding boxes (x1,y1,x2,y2)."""
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        inter_area = max(0, xB - xA) * max(0, yB - yA)
        if inter_area == 0:
            return 0.0

        areaA = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        areaB = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

        return inter_area / float(areaA + areaB - inter_area)

    def update(self, detections: List[Detection]) -> List[Tuple[Tuple[int, int, int, int], int]]:
        """
        Update tracker with new detections.
        Returns list of (bbox_xyxy, track_id).
        """
        # Prepare detection boxes
        if not detections:
            # Mark all tracks as lost
            for track in self.tracks:
                track['lost_frames'] += 1
            # Remove dead tracks
            self.tracks = [t for t in self.tracks if t['lost_frames'] <= self.max_lost_frames]
            return [(track['bbox'], track['id']) for track in self.tracks]

        det_boxes = [det.bbox for det in detections]
        matched_track_indices = set()
        matched_det_indices = set()

        # Match tracks to detections based on IOU
        for ti, track in enumerate(self.tracks):
            best_iou = 0.0
            best_di = -1
            for di, det_bbox in enumerate(det_boxes):
                if di in matched_det_indices:
                    continue
                iou = self._iou(track['bbox'], det_bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_di = di
            if best_iou >= self.iou_threshold:
                # Update track with matched detection
                track['bbox'] = det_boxes[best_di]
                track['lost_frames'] = 0
                matched_track_indices.add(ti)
                matched_det_indices.add(best_di)

        # Update lost frames for unmatched tracks
        for ti, track in enumerate(self.tracks):
            if ti not in matched_track_indices:
                track['lost_frames'] += 1

        # Create new tracks for unmatched detections
        for di, det_bbox in enumerate(det_boxes):
            if di not in matched_det_indices:
                new_track = {
                    'id': self.next_id,
                    'bbox': det_bbox,
                    'lost_frames': 0
                }
                self.tracks.append(new_track)
                self.next_id += 1

        # Remove dead tracks
        self.tracks = [t for t in self.tracks if t['lost_frames'] <= self.max_lost_frames]

        # Return active tracks
        return [(track['bbox'], track['id']) for track in self.tracks if track['lost_frames'] == 0]

    def reset(self):
        """Reset the tracker state."""
        self.tracks = []
        self.next_id = 1