#!/usr/bin/env python3
"""
Запуск всех сервисов мониторинга
"""
import asyncio
import signal
import sys
import logging
from concurrent.futures import ThreadPoolExecutor
import subprocess
import time
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('services.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ServiceManager:
    def __init__(self):
        self.processes = []
        self.running = False
        
    def start_telegram_monitor(self):
        """Запуск Telegram мониторинга"""
        try:
            logger.info("Запуск Telegram мониторинга...")
            process = subprocess.Popen([
                sys.executable, "telegram_monitor.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes.append(('telegram_monitor', process))
            logger.info("Telegram мониторинг запущен")
            return process
        except Exception as e:
            logger.error(f"Ошибка запуска Telegram мониторинга: {e}")
            return None
    
    def monitor_processes(self):
        """Мониторинг процессов и перезапуск при необходимости"""
        while self.running:
            for name, process in self.processes[:]:
                if process.poll() is not None:
                    logger.warning(f"Процесс {name} остановился, перезапускаем...")
                    self.processes.remove((name, process))
                    
                    if name == 'telegram_monitor':
                        new_process = self.start_telegram_monitor()
                        if new_process:
                            logger.info(f"Процесс {name} перезапущен")
            
            time.sleep(10)  # Проверка каждые 10 секунд
    
    def start_all(self):
        """Запуск всех сервисов"""
        logger.info("Запуск всех сервисов мониторинга...")
        self.running = True
        
        # Запуск Telegram мониторинга
        self.start_telegram_monitor()
        
        # Запуск мониторинга процессов в отдельном потоке
        monitor_thread = ThreadPoolExecutor(max_workers=1)
        monitor_thread.submit(self.monitor_processes)
        
        logger.info("Все сервисы запущены")
        
        # Ожидание завершения
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
            self.stop_all()
    
    def stop_all(self):
        """Остановка всех сервисов"""
        logger.info("Остановка всех сервисов...")
        self.running = False
        
        for name, process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"Процесс {name} остановлен")
            except subprocess.TimeoutExpired:
                process.kill()
                logger.warning(f"Процесс {name} принудительно завершен")
        
        self.processes.clear()
        logger.info("Все сервисы остановлены")

def signal_handler(signum, frame):
    """Обработчик сигналов завершения"""
    logger.info(f"Получен сигнал {signum}")
    service_manager.stop_all()
    sys.exit(0)

if __name__ == "__main__":
    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    service_manager = ServiceManager()
    
    try:
        service_manager.start_all()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        service_manager.stop_all()
        sys.exit(1)