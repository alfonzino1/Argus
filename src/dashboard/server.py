"""
Web dashboard for Real-Time Vision System.
FastAPI + WebSocket streaming with robust error handling and beautiful UI.
"""
import asyncio
import base64
import json
import logging
from typing import Optional
from queue import Queue, Empty
import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

app = FastAPI(title="Real-Time Vision Dashboard")
frame_queue: Optional[Queue] = None
event_queue: Optional[Queue] = None

def set_queues(fq: Queue, eq: Queue):
    global frame_queue, event_queue
    frame_queue = fq
    event_queue = eq
    logger.info("Queues set in dashboard server")

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; connect-src 'self' ws:; img-src 'self' data:;">
    <title>Real-Time Vision Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; background: #1e1e1e; color: #ccc; margin: 0; padding: 20px; }
        h1 { color: #00ff00; }
        #status { margin-bottom: 10px; font-size: 0.9em; }
        #container { display: flex; flex-wrap: wrap; gap: 20px; }
        #video-container { flex: 2; min-width: 640px; }
        #events-container { flex: 1; min-width: 300px; background: #2d2d2d; padding: 10px; border-radius: 5px; max-height: 80vh; overflow-y: auto; }
        #video-feed { max-width: 100%; border: 2px solid #00ff00; border-radius: 5px; }
        .event { margin-bottom: 5px; padding: 5px; border-radius: 3px; }
        .event-line_crossed { background: #4d4d1a; }
        .event-zone_enter { background: #1a4d4d; }
        .event-zone_exit { background: #4d1a1a; }
        .event-info { background: #1a4d1a; }
        .no-data { color: #ff0; }
    </style>
</head>
<body>
    <h1>Real-Time Vision System</h1>
    <div id="status">Connecting...</div>
    <div id="container">
        <div id="video-container">
            <img id="video-feed" src="" alt="Video Stream">
            <div id="placeholder" class="no-data">Waiting for video stream...</div>
        </div>
        <div id="events-container">
            <h2>Events</h2>
            <div id="events-list"></div>
        </div>
    </div>
    <script>
        const statusEl = document.getElementById('status');
        const videoImg = document.getElementById('video-feed');
        const eventsList = document.getElementById('events-list');
        const placeholder = document.getElementById('placeholder');
        const ws = new WebSocket(`ws://${window.location.host}/ws`);
        ws.onopen = () => {
            statusEl.textContent = 'Connected, waiting for stream...';
            statusEl.style.color = '#0f0';
        };
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(data);
            if (data.type === 'frame') {
                placeholder.style.display = 'none';
                videoImg.src = 'data:image/jpeg;base64,' + data.image;
            } else if (data.type === 'events') {
                const list = eventsList;
                data.events.forEach(ev => {
                    const div = document.createElement('div');
                    div.className = 'event event-' + (ev.event_type || 'info');
                    div.textContent = `[${new Date(ev.timestamp * 1000).toLocaleTimeString()}] ${ev.message}`;
                    list.appendChild(div);
                });
                eventsList.scrollTop = eventsList.scrollHeight;
            } else if (data.type === 'no_data') {
                statusEl.textContent = 'No data yet...';
            }
        };
        ws.onclose = (e) => {
            statusEl.textContent = 'Disconnected (code ' + e.code + ')';
            statusEl.style.color = '#f00';
        };
        ws.onerror = (err) => {
            statusEl.textContent = 'WebSocket error';
            console.error(err);
        };
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root():
    return DASHBOARD_HTML

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket client connected")
    try:
        while True:
            data_sent = False
            if frame_queue is not None and not frame_queue.empty():
                try:
                    frame = frame_queue.get_nowait()
                    if frame is not None and frame.shape[0] > 0 and frame.shape[1] > 0:
                        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                        jpg_b64 = base64.b64encode(buffer).decode('utf-8')
                        await websocket.send_text(json.dumps({"type": "frame", "image": jpg_b64}))
                        data_sent = True
                        logger.info("Sent frame to client")
                    else:
                        logger.warning("Invalid frame in queue")
                except Empty:
                    pass
                except Exception as e:
                    logger.error(f"Error sending frame: {e}", exc_info=True)

            if event_queue is not None and not event_queue.empty():
                events = []
                while not event_queue.empty():
                    try:
                        events.append(event_queue.get_nowait())
                    except Empty:
                        break
                if events:
                    try:
                        await websocket.send_text(json.dumps({"type": "events", "events": events}))
                        data_sent = True
                        logger.info(f"Sent {len(events)} events")
                    except Exception as e:
                        logger.error(f"Error sending events: {e}", exc_info=True)

            if not data_sent:
                await websocket.send_text(json.dumps({"type": "no_data"}))

            await asyncio.sleep(0.03)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.close(code=1011)
        except:
            pass