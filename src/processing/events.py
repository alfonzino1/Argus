"""
Event Manager for Real-Time Vision Pipeline.
Detects: object appearance/disappearance, line crossing, zone entry/exit.
"""
import logging
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class EventManager:
    """
    Manages track events and spatial triggers.

    Parameters
    ----------
    config : dict
        Configuration with optional keys:
            - lines: list of dicts {name: str, start: [x1,y1], end: [x2,y2]}
            - zones: list of dicts {name: str, points: [[x1,y1], ...]}
            - log_events: bool (default True)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config if config else {}
        self.lines = self.config.get("lines", [])
        self.zones = self.config.get("zones", [])
        self.log_events = self.config.get("log_events", True)

        # Active tracks storage: track_id -> {'first_seen_frame', 'bbox_history', ...}
        self.active_tracks: Dict[int, Dict] = {}
        self.total_objects_count = 0  # total unique tracks seen
        self.frame_count = 0
        self.events_this_frame: List[str] = []  # events generated in current frame

    def _is_point_in_zone(self, point: Tuple[float, float], zone_points: List[Tuple]) -> bool:
        """Ray casting algorithm to check if point is inside polygon."""
        x, y = point
        n = len(zone_points)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = zone_points[i]
            xj, yj = zone_points[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    @staticmethod
    def _compute_intersection(p1, p2, p3, p4):
        """Check if segment p1-p2 intersects segment p3-p4, return intersection point or None."""
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if denom == 0:
            return None  # parallel

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

        if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            return (x, y)
        return None

    def update(self, tracks: List[Tuple[Tuple[int, int, int, int], int]]):
        """
        Process current frame's tracks.
        :param tracks: list of (bbox_xyxy, track_id)
        """
        self.frame_count += 1
        self.events_this_frame = []

        current_ids = {tid for _, tid in tracks}
        # Determine which tracks disappeared
        for tid in list(self.active_tracks.keys()):
            if tid not in current_ids:
                if self.active_tracks[tid].get('active', True):
                    # Track lost
                    self.active_tracks[tid]['active'] = False
                    self.active_tracks[tid]['last_frame'] = self.frame_count
                    self._log_event(f"Object {tid} disappeared")
                else:
                    # Already marked lost, possibly remove if too long
                    if self.frame_count - self.active_tracks[tid]['last_frame'] > 30:  # max lost frames
                        del self.active_tracks[tid]

        # Process current tracks
        for bbox, tid in tracks:
            x1, y1, x2, y2 = bbox
            center = ((x1 + x2) / 2, (y1 + y2) / 2)

            if tid not in self.active_tracks:
                # New track
                self.total_objects_count += 1
                self.active_tracks[tid] = {
                    'bbox': bbox,
                    'center': center,
                    'active': True,
                    'first_frame': self.frame_count,
                    'last_frame': self.frame_count,
                    'crossed_lines': set(),  # set of line names already crossed
                    'zone_entry_triggered': set(),
                }
                self._log_event(f"Object {tid} appeared (total tracked: {self.total_objects_count})")
            else:
                prev_center = self.active_tracks[tid].get('center')
                # Update
                self.active_tracks[tid]['bbox'] = bbox
                self.active_tracks[tid]['center'] = center
                self.active_tracks[tid]['last_frame'] = self.frame_count
                self.active_tracks[tid]['active'] = True

                # Line crossing detection (if we have previous position)
                if prev_center and self.lines:
                    for line in self.lines:
                        line_name = line.get('name', 'unnamed')
                        if line_name in self.active_tracks[tid]['crossed_lines']:
                            continue
                        # Line segment from start to end
                        start = tuple(line['start'])
                        end = tuple(line['end'])
                        # Check if segment prev_center->center crosses line
                        intersection = self._compute_intersection(prev_center, center, start, end)
                        if intersection is not None:
                            self.active_tracks[tid]['crossed_lines'].add(line_name)
                            self._log_event(f"Object {tid} crossed line '{line_name}'")
                            self.events_this_frame.append({
                                'type': 'line_crossed',
                                'track_id': tid,
                                'line': line_name,
                                'point': intersection
                            })

                # Zone entry/exit (simplified: if center enters zone)
                if self.zones:
                    for zone in self.zones:
                        zone_name = zone.get('name', 'unnamed')
                        inside = self._is_point_in_zone(center, zone['points'])
                        was_inside = zone_name in self.active_tracks[tid].get('zone_inside', set())
                        if inside and not was_inside:
                            self.active_tracks[tid].setdefault('zone_inside', set()).add(zone_name)
                            self._log_event(f"Object {tid} entered zone '{zone_name}'")
                            self.events_this_frame.append({
                                'type': 'zone_enter',
                                'track_id': tid,
                                'zone': zone_name
                            })
                        elif not inside and was_inside:
                            self.active_tracks[tid]['zone_inside'].discard(zone_name)
                            self._log_event(f"Object {tid} exited zone '{zone_name}'")
                            self.events_this_frame.append({
                                'type': 'zone_exit',
                                'track_id': tid,
                                'zone': zone_name
                            })

        # Log active track count (debug)
        active_now = sum(1 for t in self.active_tracks.values() if t.get('active'))
        logger.debug(f"Frame {self.frame_count}: {active_now} active tracks, total unique: {self.total_objects_count}")

    def _log_event(self, message: str):
        if self.log_events:
            logger.info(f"EVENT: {message}")

    def get_active_bboxes_with_ids(self) -> List[Tuple[Tuple[int, int, int, int], int]]:
        """Return bboxes of currently active tracks for drawing."""
        return [(t['bbox'], tid) for tid, t in self.active_tracks.items() if t.get('active')]