#!/usr/bin/env python3
"""
Простой скрипт для постоянного мониторинга Telegram с автоперезапуском
"""
import subprocess
import time
import os
import signal
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('keep_alive.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class KeepAliveMonitor:
    def __init__(self):
        self.process = None
        self.running = True
        
    def start_telegram_monitor(self):
        """Запуск процесса мониторинга"""
        try:
            logger.info("Запуск Telegram мониторинга...")
            self.process = subprocess.Popen([
                sys.executable, "telegram_monitor.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
               universal_newlines=True, bufsize=1)
            logger.info(f"Процесс запущен с PID: {self.process.pid}")
            return True
        except Exception as e:
            logger.error(f"Ошибка запуска процесса: {e}")
            return False
    
    def monitor_process(self):
        """Мониторинг процесса и перезапуск при необходимости"""
        restart_count = 0
        max_restarts = 50  # Максимум перезапусков
        
        while self.running and restart_count < max_restarts:
            if self.process is None or self.process.poll() is not None:
                if restart_count > 0:
                    logger.warning(f"Процесс остановился. Перезапуск #{restart_count}")
                    time.sleep(5)  # Пауза перед перезапуском
                
                if self.start_telegram_monitor():
                    restart_count += 1
                else:
                    logger.error("Не удалось запустить процесс")
                    time.sleep(10)
                    continue
            
            # Проверка каждые 5 секунд
            time.sleep(5)
        
        if restart_count >= max_restarts:
            logger.error("Достигнут лимит перезапусков")
        
        logger.info("Мониторинг завершен")
    
    def stop(self):
        """Остановка мониторинга"""
        logger.info("Остановка мониторинга...")
        self.running = False
        
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                logger.warning("Процесс принудительно завершен")
        
        logger.info("Мониторинг остановлен")

# Глобальная переменная
monitor = None

def signal_handler(signum, frame):
    """Обработчик сигналов"""
    logger.info(f"Получен сигнал {signum}")
    if monitor:
        monitor.stop()
    sys.exit(0)

def main():
    global monitor
    
    logger.info("Запуск системы Keep-Alive мониторинга")
    
    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    monitor = KeepAliveMonitor()
    
    try:
        monitor.monitor_process()
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        if monitor:
            monitor.stop()

if __name__ == "__main__":
    main()