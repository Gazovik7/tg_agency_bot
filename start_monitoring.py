#!/usr/bin/env python3
"""
Start the complete monitoring system:
- Telegram bot for message collection
- Background worker for processing
- Web dashboard (already running via gunicorn)
"""

import asyncio
import logging
import signal
import sys
from concurrent.futures import ThreadPoolExecutor

from bot import TelegramMonitorBot
from worker import MessageWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MonitoringSystem:
    def __init__(self):
        self.bot = TelegramMonitorBot()
        self.worker = MessageWorker()
        self.running = False
    
    async def start(self):
        """Start all monitoring components"""
        self.running = True
        logger.info("Starting Customer Service Monitoring System...")
        
        # Start background worker and bot concurrently
        tasks = [
            asyncio.create_task(self.worker.start_worker()),
            asyncio.create_task(self.bot.start_monitoring())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in monitoring system: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop all monitoring components"""
        if self.running:
            logger.info("Stopping monitoring system...")
            await self.bot.stop_monitoring()
            self.running = False

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    sys.exit(0)

async def main():
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start monitoring system
    system = MonitoringSystem()
    try:
        await system.start()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"System error: {e}")
    finally:
        await system.stop()

if __name__ == "__main__":
    asyncio.run(main())