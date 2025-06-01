"""
Анализатор времени ответа для системы мониторинга
Отслеживает максимальное и медианное время ответа на сообщения клиентов
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from models import Message, Chat, TeamMember
from config_manager import ConfigManager

logger = logging.getLogger(__name__)


class ResponseTimeAnalyzer:
    """Анализатор времени ответа сотрудников на сообщения клиентов"""
    
    def __init__(self):
        self.config = ConfigManager()
    
    def analyze_chat_response_times(self, session: Session, chat_id: int, 
                                  start_time: datetime, end_time: datetime) -> Dict:
        """
        Анализ времени ответа для конкретного чата за период
        
        Args:
            session: Сессия базы данных
            chat_id: ID чата
            start_time: Начало периода
            end_time: Конец периода
            
        Returns:
            Словарь с метриками времени ответа
        """
        try:
            # Получаем все сообщения в указанном периоде
            messages = session.query(Message).filter(
                Message.chat_id == chat_id,
                Message.timestamp >= start_time,
                Message.timestamp <= end_time
            ).order_by(Message.timestamp).all()
            
            if not messages:
                return self._empty_response_metrics()
            
            # Анализируем диалоги и время ответа
            response_times = self._calculate_conversation_response_times(messages)
            
            if not response_times:
                return self._empty_response_metrics()
            
            # Вычисляем статистики
            return self._calculate_response_statistics(response_times)
            
        except Exception as e:
            logger.error(f"Ошибка анализа времени ответа для чата {chat_id}: {e}")
            return self._empty_response_metrics()
    
    def _calculate_conversation_response_times(self, messages: List[Message]) -> List[int]:
        """
        Рассчитывает время ответа для каждого диалога клиент-сотрудник
        
        Args:
            messages: Список сообщений, отсортированный по времени
            
        Returns:
            Список времен ответа в секундах
        """
        response_times = []
        
        # Группируем сообщения по диалогам
        current_client_message = None
        
        for message in messages:
            if not message.is_team_member:
                # Сообщение от клиента
                if current_client_message is None:
                    current_client_message = message
                else:
                    # Если предыдущее сообщение клиента не получило ответа,
                    # обновляем на более новое
                    current_client_message = message
                    
            else:
                # Сообщение от сотрудника
                if current_client_message is not None:
                    # Рассчитываем время ответа
                    response_time = (message.timestamp - current_client_message.timestamp).total_seconds()
                    
                    # Добавляем только положительные времена ответа
                    if response_time > 0:
                        response_times.append(int(response_time))
                    
                    # Сбрасываем текущее сообщение клиента
                    current_client_message = None
        
        return response_times
    
    def _calculate_response_statistics(self, response_times: List[int]) -> Dict:
        """
        Вычисляет статистики времени ответа
        
        Args:
            response_times: Список времен ответа в секундах
            
        Returns:
            Словарь со статистиками
        """
        if not response_times:
            return self._empty_response_metrics()
        
        # Сортируем для расчета медианы
        sorted_times = sorted(response_times)
        
        # Основные статистики
        avg_seconds = int(sum(response_times) / len(response_times))
        max_seconds = max(response_times)
        min_seconds = min(response_times)
        
        # Медиана
        n = len(sorted_times)
        if n % 2 == 0:
            median_seconds = int((sorted_times[n//2 - 1] + sorted_times[n//2]) / 2)
        else:
            median_seconds = sorted_times[n//2]
        
        # Перцентили
        p75_index = int(0.75 * (n - 1))
        p90_index = int(0.90 * (n - 1))
        p95_index = int(0.95 * (n - 1))
        
        p75_seconds = sorted_times[p75_index]
        p90_seconds = sorted_times[p90_index]
        p95_seconds = sorted_times[p95_index]
        
        # Конвертируем в минуты для удобства
        return {
            # В секундах
            "avg_response_time_seconds": avg_seconds,
            "max_response_time_seconds": max_seconds,
            "min_response_time_seconds": min_seconds,
            "median_response_time_seconds": median_seconds,
            "p75_response_time_seconds": p75_seconds,
            "p90_response_time_seconds": p90_seconds,
            "p95_response_time_seconds": p95_seconds,
            
            # В минутах для отображения
            "avg_response_time_minutes": round(avg_seconds / 60, 1),
            "max_response_time_minutes": round(max_seconds / 60, 1),
            "min_response_time_minutes": round(min_seconds / 60, 1),
            "median_response_time_minutes": round(median_seconds / 60, 1),
            "p75_response_time_minutes": round(p75_seconds / 60, 1),
            "p90_response_time_minutes": round(p90_seconds / 60, 1),
            "p95_response_time_minutes": round(p95_seconds / 60, 1),
            
            # Дополнительная информация
            "total_responses": len(response_times),
            "responses_under_5min": len([t for t in response_times if t <= 300]),
            "responses_under_15min": len([t for t in response_times if t <= 900]),
            "responses_under_1hour": len([t for t in response_times if t <= 3600]),
            "responses_over_1hour": len([t for t in response_times if t > 3600]),
            
            # Процентное распределение
            "percentage_under_5min": round(len([t for t in response_times if t <= 300]) / len(response_times) * 100, 1),
            "percentage_under_15min": round(len([t for t in response_times if t <= 900]) / len(response_times) * 100, 1),
            "percentage_under_1hour": round(len([t for t in response_times if t <= 3600]) / len(response_times) * 100, 1),
            "percentage_over_1hour": round(len([t for t in response_times if t > 3600]) / len(response_times) * 100, 1)
        }
    
    def _empty_response_metrics(self) -> Dict:
        """Возвращает пустые метрики, когда нет данных"""
        return {
            "avg_response_time_seconds": None,
            "max_response_time_seconds": None,
            "min_response_time_seconds": None,
            "median_response_time_seconds": None,
            "p75_response_time_seconds": None,
            "p90_response_time_seconds": None,
            "p95_response_time_seconds": None,
            
            "avg_response_time_minutes": None,
            "max_response_time_minutes": None,
            "min_response_time_minutes": None,
            "median_response_time_minutes": None,
            "p75_response_time_minutes": None,
            "p90_response_time_minutes": None,
            "p95_response_time_minutes": None,
            
            "total_responses": 0,
            "responses_under_5min": 0,
            "responses_under_15min": 0,
            "responses_under_1hour": 0,
            "responses_over_1hour": 0,
            
            "percentage_under_5min": 0,
            "percentage_under_15min": 0,
            "percentage_under_1hour": 0,
            "percentage_over_1hour": 0
        }
    
    def analyze_team_member_performance(self, session: Session, user_id: int,
                                      start_time: datetime, end_time: datetime) -> Dict:
        """
        Анализ производительности конкретного сотрудника
        
        Args:
            session: Сессия базы данных
            user_id: ID сотрудника
            start_time: Начало периода
            end_time: Конец периода
            
        Returns:
            Словарь с метриками производительности сотрудника
        """
        try:
            # Получаем все чаты, где участвовал сотрудник
            chats_with_member = session.query(Message.chat_id).filter(
                Message.user_id == user_id,
                Message.is_team_member == True,
                Message.timestamp >= start_time,
                Message.timestamp <= end_time
            ).distinct().all()
            
            if not chats_with_member:
                return self._empty_response_metrics()
            
            all_response_times = []
            total_responses = 0
            
            # Анализируем каждый чат
            for (chat_id,) in chats_with_member:
                chat_metrics = self.analyze_chat_response_times(
                    session, chat_id, start_time, end_time
                )
                
                # Получаем времена ответа только этого сотрудника
                member_response_times = self._get_member_response_times(
                    session, chat_id, user_id, start_time, end_time
                )
                
                all_response_times.extend(member_response_times)
                total_responses += len(member_response_times)
            
            if not all_response_times:
                return self._empty_response_metrics()
            
            return self._calculate_response_statistics(all_response_times)
            
        except Exception as e:
            logger.error(f"Ошибка анализа производительности сотрудника {user_id}: {e}")
            return self._empty_response_metrics()
    
    def _get_member_response_times(self, session: Session, chat_id: int, 
                                 user_id: int, start_time: datetime, end_time: datetime) -> List[int]:
        """
        Получает времена ответа конкретного сотрудника в чате
        
        Args:
            session: Сессия базы данных
            chat_id: ID чата
            user_id: ID сотрудника
            start_time: Начало периода
            end_time: Конец периода
            
        Returns:
            Список времен ответа в секундах
        """
        try:
            # Получаем сообщения сотрудника с рассчитанным временем ответа
            member_messages = session.query(Message).filter(
                Message.chat_id == chat_id,
                Message.user_id == user_id,
                Message.is_team_member == True,
                Message.timestamp >= start_time,
                Message.timestamp <= end_time,
                Message.response_time_seconds.isnot(None),
                Message.response_time_seconds > 0
            ).all()
            
            return [msg.response_time_seconds for msg in member_messages]
            
        except Exception as e:
            logger.error(f"Ошибка получения времен ответа сотрудника {user_id}: {e}")
            return []
    
    def get_slow_response_alerts(self, session: Session, hours: int = 24) -> List[Dict]:
        """
        Получает алерты о медленных ответах
        
        Args:
            session: Сессия базы данных
            hours: Количество часов для анализа
            
        Returns:
            Список алертов о медленных ответах
        """
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            end_time = datetime.utcnow()
            
            # Пороги для алертов (в минутах)
            thresholds = self.config.get_kpi_thresholds()
            slow_response_threshold = thresholds.get("max_response_time_minutes", 60)
            
            alerts = []
            
            # Получаем все активные чаты
            active_chats = session.query(Chat).filter(Chat.is_active == True).all()
            
            for chat in active_chats:
                metrics = self.analyze_chat_response_times(
                    session, chat.id, start_time, end_time
                )
                
                if (metrics["max_response_time_minutes"] and 
                    metrics["max_response_time_minutes"] > slow_response_threshold):
                    
                    alerts.append({
                        "chat_id": chat.id,
                        "chat_title": chat.title,
                        "max_response_time_minutes": metrics["max_response_time_minutes"],
                        "median_response_time_minutes": metrics["median_response_time_minutes"],
                        "total_responses": metrics["total_responses"],
                        "responses_over_1hour": metrics["responses_over_1hour"],
                        "alert_level": self._determine_alert_level(metrics["max_response_time_minutes"])
                    })
            
            # Сортируем по максимальному времени ответа
            alerts.sort(key=lambda x: x["max_response_time_minutes"], reverse=True)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Ошибка получения алертов медленных ответов: {e}")
            return []
    
    def _determine_alert_level(self, max_response_minutes: float) -> str:
        """Определяет уровень алерта на основе времени ответа"""
        if max_response_minutes > 480:  # 8 часов
            return "critical"
        elif max_response_minutes > 240:  # 4 часа
            return "high"
        elif max_response_minutes > 60:  # 1 час
            return "medium"
        else:
            return "low"