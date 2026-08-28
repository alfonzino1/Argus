"""Tests for camera capture module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np


class TestCameraStream:
    """Test cases for CameraStream class."""

    @patch('src.camera.capture.cv2.VideoCapture')
    def test_camera_initialization(self, mock_video_capture):
        """Test camera stream initialization."""
        from src.camera.capture import CameraStream
        
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_video_capture.return_value = mock_cap
        
        camera = CameraStream(source=0)
        
        assert camera.source == 0
        assert camera.config["buffer_size"] == 1
        # VideoCapture is not called during init, only during start()
        assert not mock_video_capture.called

    @patch('src.camera.capture.cv2.VideoCapture')
    def test_camera_start(self, mock_video_capture):
        """Test camera start method."""
        from src.camera.capture import CameraStream
        
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_video_capture.return_value = mock_cap
        
        camera = CameraStream(source=0)
        camera.start()
        
        assert camera.is_running
        assert mock_cap.isOpened.called

    @patch('src.camera.capture.cv2.VideoCapture')
    def test_camera_read_success(self, mock_video_capture):
        """Test successful frame read."""
        from src.camera.capture import CameraStream
        
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_video_capture.return_value = mock_cap
        
        camera = CameraStream(source=0)
        camera.start()
        
        ret, frame = camera.read()
        
        assert ret is True
        assert frame is not None
        camera.stop()

    @patch('src.camera.capture.cv2.VideoCapture')
    def test_camera_read_failure(self, mock_video_capture):
        """Test failed frame read."""
        from src.camera.capture import CameraStream
        
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)
        mock_video_capture.return_value = mock_cap
        
        camera = CameraStream(source=0)
        camera.start()
        
        ret, frame = camera.read()
        
        assert ret is False
        assert frame is None
        camera.stop()

    @patch('src.camera.capture.cv2.VideoCapture')
    def test_camera_stop(self, mock_video_capture):
        """Test camera stop method."""
        from src.camera.capture import CameraStream
        
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_video_capture.return_value = mock_cap
        
        camera = CameraStream(source=0)
        camera.start()
        camera.stop()
        
        assert not camera.is_running
        assert mock_cap.release.called

    @patch('src.camera.capture.cv2.VideoCapture')
    def test_camera_reconnect_config(self, mock_video_capture):
        """Test camera reconnect configuration."""
        from src.camera.capture import CameraStream
        
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_video_capture.return_value = mock_cap
        
        camera = CameraStream(source=0, config={"reconnect_delay": 0.1})
        
        assert camera.config["reconnect_delay"] == 0.1
        assert camera._reconnect_delay == 0.1