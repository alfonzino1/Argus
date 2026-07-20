"""
Run the web dashboard server.
Usage: python dashboard.py [--port 8000]
"""
import argparse
import logging
import queue

from src.dashboard.server import app, set_queues

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dashboard")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # Create queues for inter-process communication with pipeline
    frame_queue = queue.Queue(maxsize=10)
    event_queue = queue.Queue(maxsize=100)
    set_queues(frame_queue, event_queue)
    logger.info(f"Dashboard queues created. Connect pipeline to these queues.")
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=args.port)