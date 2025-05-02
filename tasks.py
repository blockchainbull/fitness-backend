"""
Background task processing for FitMind AI.
"""
# tasks.py
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Thread pool for running background tasks
_executor = ThreadPoolExecutor(max_workers=2)
_task_queue = asyncio.Queue()
_is_worker_running = False

async def _background_worker():
    """Worker that processes queued tasks."""
    global _is_worker_running
    _is_worker_running = True
    
    try:
        while True:
            try:
                # Get a task from the queue
                task_func, args, kwargs = await _task_queue.get()
                
                # Execute the task
                try:
                    await task_func(*args, **kwargs)
                except Exception as e:
                    print(f"Error executing background task: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Mark the task as done
                _task_queue.task_done()
                
            except asyncio.CancelledError:
                break
    finally:
        _is_worker_running = False

def start_background_worker():
    """Start the background worker if not already running."""
    global _is_worker_running
    if not _is_worker_running:
        asyncio.create_task(_background_worker())

async def queue_task(func, *args, **kwargs):
    """Queue a generic task to be executed by the background worker."""
    # Add task to queue
    await _task_queue.put((func, args, kwargs))
    
    # Ensure worker is running
    start_background_worker()