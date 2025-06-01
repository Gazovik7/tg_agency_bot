
#!/usr/bin/env python3
"""
Тест анализа тональности для 3 тестовых сообщений от клиентов
"""
import asyncio
import logging
from sentiment_analyzer import SentimentAnalyzer

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_client_messages():
    """Тестирование анализа тональности для клиентских сообщений"""
    
    # Создаем анализатор тональности
    analyzer = SentimentAnalyzer()
    
    # 3 тестовых сообщения от клиентов
    test_messages = [
        "Спасибо! Хороший результат",
        "Когда будет готова работа?",
        "Это ужас! Переделывайте!"
    ]
    
    logger.info("🔍 Начинаем анализ тональности тестовых сообщений...")
    logger.info("=" * 60)
    
    for i, message in enumerate(test_messages, 1):
        logger.info(f"\n📝 Сообщение {i}: '{message}'")
        
        try:
            # Анализируем тональность
            result = await analyzer.analyze_sentiment(message)
            
            if result:
                score = result['score']
                label = result['label']
                confidence = result['confidence']
                
                # Определяем эмодзи для тональности
                emoji = "😊" if label == "positive" else "😠" if label == "negative" else "😐"
                
                logger.info(f"   {emoji} Тональность: {label.upper()}")
                logger.info(f"   📊 Оценка: {score:.3f} (-1 до 1)")
                logger.info(f"   🎯 Уверенность: {confidence:.3f} (0 до 1)")
                
                # Дополнительная интерпретация
                if label == "positive":
                    interpretation = "Клиент доволен"
                elif label == "negative":
                    interpretation = "Клиент недоволен - требует внимания!"
                else:
                    interpretation = "Нейтральный запрос"
                
                logger.info(f"   💡 Интерпретация: {interpretation}")
                
            else:
                logger.error("   ❌ Не удалось проанализировать сообщение")
                
        except Exception as e:
            logger.error(f"   ❌ Ошибка при анализе: {e}")
        
        logger.info("-" * 40)
    
    logger.info("\n✅ Анализ завершен!")

if __name__ == "__main__":
    asyncio.run(test_client_messages())
