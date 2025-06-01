#!/usr/bin/env python3
"""
Keep Telegram monitor alive with auto-restart
"""
import subprocess
import time
import os
import signal
import sys

def start_telegram_monitor():
    """Start Telegram monitor process"""
    return subprocess.Popen([
        'python', 'run_telegram_monitor.py'
    ], cwd='/home/runner/workspace')

def main():
    """Main monitoring loop"""
    process = None
    
    def signal_handler(signum, frame):
        if process:
            process.terminate()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Starting Telegram monitor keeper...")
    
    while True:
        try:
            if process is None or process.poll() is not None:
                if process:
                    print("Telegram monitor stopped, restarting...")
                else:
                    print("Starting Telegram monitor...")
                
                process = start_telegram_monitor()
                print(f"Telegram monitor started with PID {process.pid}")
            
            time.sleep(10)  # Check every 10 seconds
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
    
    if process:
        process.terminate()

if __name__ == "__main__":
    main()