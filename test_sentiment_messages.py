
#!/usr/bin/env python3
"""
Скрипт для добавления тестовых сообщений и анализа их тональности
"""

import asyncio
import logging
import os
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Message, Chat
from sentiment_analyzer import SentimentAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SentimentTester:
    """Тестер для анализа тональности сообщений"""
    
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
    
    def add_test_messages(self):
        """Добавляем тестовые сообщения"""
        # Получаем первый доступный чат
        chat = self.session.query(Chat).first()
        if not chat:
            logger.error("Нет доступных чатов в базе данных")
            return []
        
        test_messages = [
            "Спасибо! Хороший результат",
            "Когда будет готова работа?",
            "Это ужас! Переделывайте!"
        ]
        
        added_messages = []
        
        for i, text in enumerate(test_messages, 1):
            message = Message(
                message_id=999000 + i,  # Уникальные ID для тестов
                chat_id=chat.id,
                user_id=999999,  # Тестовый пользователь
                username="test_client",
                full_name="Тестовый Клиент",
                text=text,
                message_type='text',
                is_team_member=False,  # Клиентское сообщение
                timestamp=datetime.utcnow(),
                processed_for_sentiment=False
            )
            
            self.session.add(message)
            added_messages.append(message)
            logger.info(f"Добавлено сообщение {i}: '{text}'")
        
        self.session.commit()
        logger.info(f"Добавлено {len(added_messages)} тестовых сообщений")
        return added_messages
    
    async def analyze_test_messages(self, messages):
        """Анализируем тональность тестовых сообщений"""
        logger.info("Начинаем анализ тональности тестовых сообщений...")
        
        for message in messages:
            logger.info(f"\nАнализируем: '{message.text}'")
            
            try:
                # Анализируем тональность
                sentiment_result = await self.sentiment_analyzer.analyze_sentiment(message.text)
                
                if sentiment_result:
                    # Обновляем сообщение в базе
                    message.sentiment_score = sentiment_result['score']
                    message.sentiment_label = sentiment_result['label']
                    message.sentiment_confidence = sentiment_result['confidence']
                    message.processed_for_sentiment = True
                    
                    # Выводим результат
                    score = sentiment_result['score']
                    label = sentiment_result['label']
                    confidence = sentiment_result['confidence']
                    
                    logger.info(f"✓ Результат анализа:")
                    logger.info(f"  - Тональность: {label.upper()}")
                    logger.info(f"  - Оценка: {score:.3f} (от -1 до 1)")
                    logger.info(f"  - Уверенность: {confidence:.3f} (от 0 до 1)")
                    
                    # Добавляем эмодзи для наглядности
                    if label == 'positive':
                        emoji = "😊"
                    elif label == 'negative':
                        emoji = "😠"
                    else:
                        emoji = "😐"
                    
                    print(f"  {emoji} '{message.text}' -> {label.upper()} ({score:.2f})")
                    
                else:
                    logger.warning(f"❌ Не удалось проанализировать: '{message.text}'")
                    message.processed_for_sentiment = True
                
                # Пауза между запросами
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Ошибка при анализе '{message.text}': {e}")
        
        # Сохраняем все изменения
        self.session.commit()
        logger.info("\n✅ Анализ завершен и результаты сохранены в базу данных")
    
    async def run_test(self):
        """Запуск полного теста"""
        try:
            # Проверяем API ключ
            if not self.sentiment_analyzer.api_key:
                logger.error("❌ OPENROUTER_API_KEY не найден!")
                logger.info("Добавьте API ключ через Secrets tool в Replit")
                return
            
            logger.info("🚀 Запускаем тест анализа тональности...")
            
            # Добавляем тестовые сообщения
            test_messages = self.add_test_messages()
            
            if not test_messages:
                logger.error("❌ Не удалось добавить тестовые сообщения")
                return
            
            # Анализируем тональность
            await self.analyze_test_messages(test_messages)
            
            # Показываем итоговую статистику
            self.show_results_summary(test_messages)
            
        except Exception as e:
            logger.error(f"❌ Ошибка в тесте: {e}")
        finally:
            self.session.close()
    
    def show_results_summary(self, messages):
        """Показываем итоговую сводку результатов"""
        logger.info("\n📊 ИТОГОВАЯ СВОДКА:")
        logger.info("=" * 50)
        
        for i, message in enumerate(messages, 1):
            text = message.text
            label = message.sentiment_label or "не определено"
            score = message.sentiment_score or 0
            confidence = message.sentiment_confidence or 0
            
            if label == 'positive':
                emoji = "😊"
            elif label == 'negative':
                emoji = "😠"
            else:
                emoji = "😐"
            
            logger.info(f"{i}. {emoji} '{text}'")
            logger.info(f"   → {label.upper()} | Оценка: {score:.2f} | Уверенность: {confidence:.2f}")
            logger.info("")


async def main():
    """Основная функция"""
    tester = SentimentTester()
    await tester.run_test()


if __name__ == "__main__":
    print("🧪 Тест анализа тональности сообщений")
    print("=" * 40)
    asyncio.run(main())
