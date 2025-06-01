#!/usr/bin/env python3
"""
Скрипт для анализа тональности существующих сообщений
Анализирует все сообщения клиентов и обновляет базу данных
"""

import asyncio
import logging
import os
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from sentiment_analyzer import SentimentAnalyzer

Base = declarative_base()

class Message(Base):
    """Упрощенная модель сообщения для анализа тональности"""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    text = Column(Text)
    is_team_member = Column(Boolean, nullable=False)
    sentiment_score = Column(Float)
    sentiment_label = Column(String(20))
    sentiment_confidence = Column(Float)
    processed_for_sentiment = Column(Boolean, default=False)
    timestamp = Column(DateTime)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SentimentBatchAnalyzer:
    """Пакетный анализатор тональности сообщений"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.setup_database()
    
    def setup_database(self):
        """Настройка подключения к базе данных"""
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL не найден в переменных окружения")
        
        self.engine = create_engine(database_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    async def analyze_all_client_messages(self):
        """Анализ всех сообщений клиентов"""
        logger.info("Начинаем анализ тональности сообщений клиентов...")
        
        # Получаем все сообщения клиентов без анализа тональности
        unanalyzed_messages = self.session.query(Message).filter(
            Message.is_team_member == False,  # Только клиентские сообщения
            Message.text.isnot(None),  # Только текстовые сообщения
            Message.text != '',  # Не пустые
            (Message.processed_for_sentiment == False) | (Message.processed_for_sentiment.is_(None))  # Не обработанные или NULL
        ).all()
        
        logger.info(f"Найдено {len(unanalyzed_messages)} сообщений для анализа")
        
        if not unanalyzed_messages:
            logger.info("Нет сообщений для анализа")
            return
        
        analyzed_count = 0
        error_count = 0
        
        for message in unanalyzed_messages:
            try:
                logger.info(f"Анализируем сообщение {message.id}: '{message.text[:50]}...'")
                
                # Анализируем тональность
                sentiment_result = await self.sentiment_analyzer.analyze_sentiment(message.text)
                
                if sentiment_result:
                    # Обновляем сообщение
                    message.sentiment_score = sentiment_result['score']
                    message.sentiment_label = sentiment_result['label']
                    message.sentiment_confidence = sentiment_result['confidence']
                    message.processed_for_sentiment = True
                    
                    logger.info(f"Результат: {sentiment_result['label']} (score: {sentiment_result['score']:.2f})")
                    analyzed_count += 1
                else:
                    logger.warning(f"Не удалось проанализировать сообщение {message.id}")
                    # Помечаем как обработанное, чтобы не пытаться снова
                    message.processed_for_sentiment = True
                    error_count += 1
                
                # Сохраняем изменения каждые 5 сообщений
                if (analyzed_count + error_count) % 5 == 0:
                    self.session.commit()
                    logger.info(f"Обработано {analyzed_count + error_count} сообщений")
                
                # Небольшая пауза между запросами к API
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Ошибка при анализе сообщения {message.id}: {e}")
                error_count += 1
                continue
        
        # Финальное сохранение
        self.session.commit()
        
        logger.info(f"Анализ завершен:")
        logger.info(f"- Успешно проанализировано: {analyzed_count}")
        logger.info(f"- Ошибок: {error_count}")
        logger.info(f"- Всего обработано: {analyzed_count + error_count}")
    
    async def analyze_recent_messages(self, hours: int = 24):
        """Анализ сообщений за последние часы"""
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent_messages = self.session.query(Message).filter(
            Message.is_team_member == False,
            Message.text.isnot(None),
            Message.text != '',
            Message.timestamp >= cutoff_time,
            Message.processed_for_sentiment == False
        ).all()
        
        logger.info(f"Найдено {len(recent_messages)} недавних сообщений для анализа")
        
        analyzed_count = 0
        for message in recent_messages:
            try:
                sentiment_result = await self.sentiment_analyzer.analyze_sentiment(message.text)
                
                if sentiment_result:
                    message.sentiment_score = sentiment_result['score']
                    message.sentiment_label = sentiment_result['label']
                    message.sentiment_confidence = sentiment_result['confidence']
                    message.processed_for_sentiment = True
                    analyzed_count += 1
                    
                await asyncio.sleep(0.5)  # Короткая пауза
                
            except Exception as e:
                logger.error(f"Ошибка при анализе сообщения {message.id}: {e}")
        
        self.session.commit()
        logger.info(f"Проанализировано {analyzed_count} недавних сообщений")
    
    def get_statistics(self):
        """Получение статистики по анализу тональности"""
        total_messages = self.session.query(Message).filter(
            Message.is_team_member == False,
            Message.text.isnot(None),
            Message.text != ''
        ).count()
        
        analyzed_messages = self.session.query(Message).filter(
            Message.is_team_member == False,
            Message.processed_for_sentiment == True
        ).count()
        
        positive_count = self.session.query(Message).filter(
            Message.sentiment_label == 'positive'
        ).count()
        
        negative_count = self.session.query(Message).filter(
            Message.sentiment_label == 'negative'
        ).count()
        
        neutral_count = self.session.query(Message).filter(
            Message.sentiment_label == 'neutral'
        ).count()
        
        logger.info("Статистика анализа тональности:")
        logger.info(f"- Всего клиентских сообщений: {total_messages}")
        logger.info(f"- Проанализировано: {analyzed_messages}")
        logger.info(f"- Позитивные: {positive_count}")
        logger.info(f"- Негативные: {negative_count}")
        logger.info(f"- Нейтральные: {neutral_count}")
        
        return {
            'total': total_messages,
            'analyzed': analyzed_messages,
            'positive': positive_count,
            'negative': negative_count,
            'neutral': neutral_count
        }
    
    def close(self):
        """Закрытие соединения с базой данных"""
        self.session.close()


async def main():
    """Основная функция"""
    analyzer = SentimentBatchAnalyzer()
    
    try:
        # Показываем статистику до анализа
        logger.info("Статистика до анализа:")
        analyzer.get_statistics()
        
        # Запускаем анализ всех сообщений
        await analyzer.analyze_all_client_messages()
        
        # Показываем статистику после анализа
        logger.info("Статистика после анализа:")
        analyzer.get_statistics()
        
    finally:
        analyzer.close()


if __name__ == "__main__":
    asyncio.run(main())