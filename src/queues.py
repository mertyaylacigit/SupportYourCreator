import time
import logging
import sys
import os
import asyncio
from config import LOGGING_LEVEL
import psutil


# ✅ Setup logging configuration
logging.basicConfig(
        level=LOGGING_LEVEL,  # Capture ALL logs (INFO, DEBUG, ERROR)  # Set to DEBUG if you want to see debug logs of discord.http's request function
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
                logging.StreamHandler(sys.stdout)  # Ensure logs are printed to Replit console
        ]
)
logger = logging.getLogger(__name__)  # ✅ Use logger instead of print()


# DISCORD API RATE LIMIT QUEUE SYSTEM

class RateLimitQueue:
    """
    This class implements a rate limit queue for handling rate limits. You can use "await rate_limiter.add_request(func, args, kwargs)"
    in order to run it in the queue. If you only want to run it once (e.g. in on_ready()), you can also use "await func(*args, **kwargs)" thats no problem.
    """
    def __init__(self, max_requests_per_second):
        self.queue = asyncio.Queue()
        self.max_requests_per_second = max_requests_per_second
        self.requests_this_second = 0
        self.current_second = int(time.time())
        self.lock = asyncio.Lock()
        logger.debug(f"Rate Limit Queue items: {self.queue.qsize()}")

    async def add_request(self, func, args, kwargs):
        future = asyncio.get_event_loop().create_future()
        await self.queue.put((func, args, kwargs, future))
        return await future  # Wartet auf das Ergebnis

    async def request_handler(self, request_method, args, kwargs, current_sec, requests_this_second, future):
        try:
            if request_method == print:
                result = f"Processing request: {args}, {round(time.time()%10,2)}, {round(current_sec%10,3)}, {requests_this_second}"
                logger.debug(result)
            else:
                result = f"🚦 Processing request: {request_method.__name__}, {kwargs['content'] if 'content' in kwargs else ''}, {round(time.time()%10,2)}, {round(current_sec%10,3)}, {requests_this_second}"
                logger.debug(result)
                response = await request_method(*args, **kwargs)
                future.set_result(response)  # Setze das Future-Ergebnis

        except Exception as e:
            future.set_exception(e)


    async def worker(self):
        while True:
            request_method, args, kwargs, future = await self.queue.get()  # Future mit aus der Queue holen
            async with self.lock:
                now = int(time.time())
                if now != self.current_second:
                        self.current_second = now
                        self.requests_this_second = 0
                        
                if self.requests_this_second >= self.max_requests_per_second:
                        await asyncio.sleep(1 - (time.time() % 1))
                        self.current_second = int(time.time())
                        self.requests_this_second = 0
                self.requests_this_second += 1

            # Erstelle Task und setze das Future-Ergebnis
            asyncio.create_task(self.request_handler(request_method, args, kwargs, self.current_second, self.requests_this_second, future))
            await asyncio.sleep(1 / self.max_requests_per_second) 
            self.queue.task_done()
            logger.debug(f"Rate Limit Queue items: {self.queue.qsize()}")



# --- END OF DISCORD API RATE LIMIT QUEUE SYSTEM ---


# DATABASE QUEUE

class BaseDBQueue:
    """
    Queue system for handling DB writes efficiently.
    This ensures that DB writes happen asynchronously without blocking the main event loop.
    It is mainly used to send user data to the database.
    """
    def __init__(self, name, max_workers=1):
        self.queue = asyncio.Queue()
        self.name = name
        self.max_workers = max_workers
        self.lock = asyncio.Lock()  # Not really needed for PG, but keeping it for uniformity
        logger.debug(f"{self.name} Queue items: {self.queue.qsize()}")
        
    async def add_task(self, func, *args, **kwargs):
        """Add a database write operation to the queue."""
        future = asyncio.get_event_loop().create_future()
        await self.queue.put((func, args, kwargs, future))
        logger.debug(f"Added task to {self.name} queue args: {args}")
        return await future  # Waits for the result


    async def worker(self):
        """Worker function that continuously processes tasks from the queue."""
        while True:
            func, args, kwargs, future = await self.queue.get()
            try:
                logger.debug(f"{self.name}🚦 Processing request: {func.__name__}, args: {args}")
                response = await func(*args, **kwargs)  # Execute DB save
                future.set_result(response)  # Set the result
                logger.info(f"✅ Successfully saved to {self.name}: {args}")
            except Exception as e:
                logger.error(f"❌ Error processing {self.name} task: {e}")
                future.set_exception(e)
            finally:
                self.queue.task_done()
                logger.debug(f"{self.name} queue task done. Queue items: {self.queue.qsize()}")

    async def start_workers(self):
        """Start multiple workers for parallel processing. For now: 1 worker, hence sequential"""
        for i in range(self.max_workers):
            asyncio.create_task(self.worker())
            logger.info(f"✅ Started {self.name} worker {i}")


class PGQueue(BaseDBQueue):
    """Queue system for handling PostgreSQL writes asynchronously."""
    def __init__(self, max_workers=1):
        super().__init__(name="PostgreSQL", max_workers=max_workers)

class ObjectStorageQueue(BaseDBQueue):
    """Queue system for handling object storage uploads asynchronously."""
    def __init__(self, max_workers=1):
        super().__init__(name="Object Storage", max_workers=max_workers)

# --- END OF DATABASE QUEUE ---



# --- Queue for CPU Intensive Tasks

class CpuIntensiveQueue:
    """
    Queue system for handling CPU-intensive tasks asynchronously.
    It prevents CPU overload by limiting the number of concurrent CPU-heavy tasks.
    """

    def __init__(self, max_workers=2):
        self.queue = asyncio.Queue()
        self.max_workers = max_workers  # Limit parallel CPU-heavy tasks
        self.semaphore = asyncio.Semaphore(max_workers)  # Controls concurrency
        logger.debug(f"CpuIntensiveQueue initialized. Queue size: {self.queue.qsize()}")

    async def add_task(self, func, *args, **kwargs):
        """Add a CPU-heavy task to the queue."""
        future = asyncio.get_event_loop().create_future()
        await self.queue.put((func, args, kwargs, future))
        logger.debug(f"🖥️ Added CPU task: {func.__name__}, args: {args}")
        return await future  # Waits for the result

    async def worker(self):
        """Worker function that processes CPU-heavy tasks."""
        while True:
            cpu_usage = psutil.cpu_percent()  # Get current CPU usage
            logger.info(f"⚙️ CPU Usage: {cpu_usage}%")
            func, args, kwargs, future = await self.queue.get()
            async with self.semaphore:  # Limits concurrent CPU-heavy tasks
                try:
                    logger.debug(f"🖥️ Processing CPU task: {func.__name__}, args: {args}")
                    start_time = time.time()

                    # Run CPU-heavy task in an executor to avoid blocking the event loop
                    loop = asyncio.get_running_loop()
                    response = await loop.run_in_executor(None, func, *args, **kwargs)

                    future.set_result(response)  # Return result
                    logger.info(f"✅ CPU task {func.__name__} completed in {time.time() - start_time:.2f}s")
                except Exception as e:
                    logger.error(f"❌ Error processing CPU task: {e}")
                    future.set_exception(e)
                finally:
                    self.queue.task_done()
                    logger.debug(f"CpuIntensiveQueue task done. Remaining: {self.queue.qsize()}")

    async def start_workers(self):
        """Starts multiple workers for parallel CPU processing (limited by max_workers)."""
        for i in range(self.max_workers):
            asyncio.create_task(self.worker())
            logger.info(f"✅ Started CpuIntensiveQueue worker {i}")

# --- END OF CPU Intensive Queue ---





