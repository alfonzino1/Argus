"""
Web dashboard for Real-Time Vision System.
FastAPI + WebSocket streaming with robust error handling, authentication, and beautiful UI.
"""
import asyncio
import base64
import json
import logging
from typing import Optional
from queue import Queue, Empty
from datetime import timedelta, datetime
import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from src.utils.auth import (
    authenticate_user,
    create_access_token,
    decode_access_token,
    _get_default_users,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Real-Time Vision Dashboard")
frame_queue: Optional[Queue] = None
event_queue: Optional[Queue] = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

def set_queues(fq: Queue, eq: Queue):
    global frame_queue, event_queue
    frame_queue = fq
    event_queue = eq
    logger.info("Queues set in dashboard server")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Optional[dict]:
    """Get current authenticated user from JWT token."""
    if not token:
        return None
    
    payload = decode_access_token(token)
    if payload is None:
        return None
    
    username: str = payload.get("sub")
    if username is None:
        return None
    
    users = _get_default_users()
    user = users.get(username)
    if user is None or user.get("disabled"):
        return None
    
    return user


class Token(BaseModel):
    access_token: str
    token_type: str


DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; connect-src 'self' ws: wss:; img-src 'self' data:;">
    <title>Real-Time Vision Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; background: #1e1e1e; color: #ccc; margin: 0; padding: 20px; }
        h1 { color: #00ff00; }
        #status { margin-bottom: 10px; font-size: 0.9em; }
        #login-container { max-width: 400px; margin: 100px auto; padding: 30px; background: #2d2d2d; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        #login-container h2 { color: #00ff00; text-align: center; margin-bottom: 20px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #aaa; }
        .form-group input { width: 100%; padding: 10px; border: 1px solid #444; border-radius: 5px; background: #1a1a1a; color: #fff; box-sizing: border-box; }
        .form-group input:focus { outline: none; border-color: #00ff00; }
        button { width: 100%; padding: 12px; background: #00ff00; color: #000; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; font-size: 16px; }
        button:hover { background: #00cc00; }
        #error-message { color: #ff4444; text-align: center; margin-top: 10px; display: none; }
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
        #logout-btn { position: absolute; top: 20px; right: 20px; padding: 8px 16px; background: #ff4444; color: white; border: none; border-radius: 5px; cursor: pointer; display: none; }
        #user-info { position: absolute; top: 20px; right: 150px; color: #aaa; display: none; }
    </style>
</head>
<body>
    <button id="logout-btn" onclick="logout()">Logout</button>
    <div id="user-info">Logged in as: <span id="username-display"></span></div>
    
    <div id="login-container">
        <h2>Dashboard Login</h2>
        <div class="form-group">
            <label for="username">Username</label>
            <input type="text" id="username" placeholder="Enter username" value="admin">
        </div>
        <div class="form-group">
            <label for="password">Password</label>
            <input type="password" id="password" placeholder="Enter password" value="changeme">
        </div>
        <button onclick="login()">Login</button>
        <div id="error-message"></div>
    </div>
    
    <div id="main-content" style="display: none;">
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
    </div>
    
    <script>
        let accessToken = null;
        let ws = null;
        
        function showError(msg) {
            const errorEl = document.getElementById('error-message');
            errorEl.textContent = msg;
            errorEl.style.display = 'block';
        }
        
        function hideError() {
            document.getElementById('error-message').style.display = 'none';
        }
        
        async function login() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            if (!username || !password) {
                showError('Please enter both username and password');
                return;
            }
            
            try {
                const formData = new URLSearchParams();
                formData.append('username', username);
                formData.append('password', password);
                
                const response = await fetch('/token', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: formData,
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Login failed');
                }
                
                const data = await response.json();
                accessToken = data.access_token;
                localStorage.setItem('accessToken', accessToken);
                
                showMainContent(username);
                connectWebSocket();
            } catch (err) {
                showError(err.message);
            }
        }
        
        function showMainContent(username) {
            document.getElementById('login-container').style.display = 'none';
            document.getElementById('main-content').style.display = 'block';
            document.getElementById('logout-btn').style.display = 'block';
            document.getElementById('user-info').style.display = 'block';
            document.getElementById('username-display').textContent = username;
        }
        
        function logout() {
            accessToken = null;
            localStorage.removeItem('accessToken');
            if (ws) {
                ws.close();
                ws = null;
            }
            document.getElementById('login-container').style.display = 'block';
            document.getElementById('main-content').style.display = 'none';
            document.getElementById('logout-btn').style.display = 'none';
            document.getElementById('user-info').style.display = 'none';
            document.getElementById('video-feed').src = '';
            document.getElementById('placeholder').style.display = 'block';
            document.getElementById('events-list').innerHTML = '';
            hideError();
        }
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(protocol + '//' + window.location.host + '/ws?token=' + accessToken);
            
            const statusEl = document.getElementById('status');
            const videoImg = document.getElementById('video-feed');
            const eventsList = document.getElementById('events-list');
            const placeholder = document.getElementById('placeholder');
            
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
                        div.textContent = '[' + new Date(ev.timestamp * 1000).toLocaleTimeString() + '] ' + ev.message;
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
        }
        
        window.onload = () => {
            const storedToken = localStorage.getItem('accessToken');
            if (storedToken) {
                accessToken = storedToken;
                try {
                    const payload = JSON.parse(atob(storedToken.split('.')[1]));
                    const username = payload.sub;
                    if (username) {
                        showMainContent(username);
                        connectWebSocket();
                    }
                } catch (e) {
                    localStorage.removeItem('accessToken');
                }
            }
        };
    </script>
</body>
</html>
"""


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 token endpoint for authentication."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=60)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the dashboard HTML page."""
    return DASHBOARD_HTML


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """WebSocket endpoint for real-time video and events streaming."""
    if token:
        user = await get_current_user(token)
        if not user:
            await websocket.close(code=4001, reason="Invalid or expired token")
            return
    else:
        logger.warning("WebSocket connection without token - consider requiring authentication")
    
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
                        logger.debug("Sent frame to client")
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/v1/status")
async def api_status():
    """API status endpoint with basic system info."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "dashboard_active": frame_queue is not None,
        "events_active": event_queue is not None,
    }
