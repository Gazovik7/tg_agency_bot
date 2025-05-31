#!/usr/bin/env python3
"""
Run the complete monitoring system
"""
import asyncio
import logging
import os
import signal
import sys
from start_monitoring import MonitoringSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Global monitoring system instance
monitoring_system = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    if monitoring_system:
        asyncio.create_task(monitoring_system.stop())
    sys.exit(0)

async def main():
    """Main function"""
    global monitoring_system
    
    # Set environment variables
    os.environ['REDIS_URL'] = 'redis://localhost:6379'
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting Customer Service Monitoring System...")
    
    try:
        monitoring_system = MonitoringSystem()
        await monitoring_system.start()
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down by user request...")
    except Exception as e:
        logger.error(f"Error in monitoring system: {e}")
    finally:
        if monitoring_system:
            await monitoring_system.stop()

if __name__ == "__main__":
    asyncio.run(main())