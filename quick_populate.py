#!/usr/bin/env python3
"""
Быстрый скрипт для заполнения базы данных тестовыми данными
"""

import os
import sys
from datetime import datetime, timedelta
import random
from sqlalchemy import create_engine, text

# Настройка подключения к базе данных
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("Ошибка: переменная DATABASE_URL не установлена")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

# Данные для тестовых чатов
TEST_CHATS = [
    {"id": -1001111111111, "title": "Веб-разработка для ООО Альфа", "chat_type": "supergroup"},
    {"id": -1001111111112, "title": "Мобильное приложение для ИП Петров", "chat_type": "supergroup"},
    {"id": -1001111111113, "title": "Интернет-магазин для Бета Трейд", "chat_type": "supergroup"},
    {"id": -1001111111114, "title": "CRM система для Гамма Консалтинг", "chat_type": "supergroup"},
    {"id": -1001111111115, "title": "Лендинг для стартапа TechVision", "chat_type": "supergroup"},
]

# Команда сотрудников
TEAM_MEMBERS = [
    {"user_id": 100001, "username": "project_manager", "full_name": "Анна Проектова", "role": "Project Manager"},
    {"user_id": 100002, "username": "senior_dev", "full_name": "Максим Разработкин", "role": "Senior Developer"},
    {"user_id": 100003, "username": "frontend_dev", "full_name": "Елена Фронтендова", "role": "Frontend Developer"},
]

# Клиенты для каждого чата
CLIENT_PROFILES = [
    [{"user_id": 200001, "username": "alfa_ceo", "full_name": "Иван Альфин"}],
    [{"user_id": 200003, "username": "petrov_ip", "full_name": "Сергей Петров"}],
    [{"user_id": 200004, "username": "beta_owner", "full_name": "Мария Бетина"}],
    [{"user_id": 200006, "username": "gamma_director", "full_name": "Алексей Гаммин"}],
    [{"user_id": 200007, "username": "tech_founder", "full_name": "Анастасия Визионова"}],
]

# Шаблоны сообщений
CLIENT_MESSAGES = [
    "Привет! Как дела с проектом?",
    "Когда будет готов первый прототип?",
    "Можно посмотреть текущий прогресс?",
    "У меня есть несколько замечаний по дизайну",
    "Отличная работа! Мне нравится",
    "Нужно внести небольшие правки",
    "Когда планируете завершить этап?",
    "Есть вопросы по функционалу",
    "Спасибо за оперативность!",
    "Можем обсудить детали завтра?",
]

TEAM_MESSAGES = [
    "Добрый день! Работаем над вашим проектом",
    "Прототип будет готов к концу недели",
    "Отправил вам ссылку на текущую версию",
    "Учтем все ваши замечания в следующей итерации",
    "Спасибо! Рады, что вам нравится",
    "Внесем правки в ближайшие дни",
    "Планируем завершить к пятнице",
    "Готов обсудить все детали",
    "Всегда пожалуйста! Обращайтесь",
    "Конечно, созвонимся завтра в 14:00",
]

def create_test_data():
    """Создание тестовых данных"""
    connection = engine.connect()
    trans = connection.begin()
    
    try:
        print("Очистка старых тестовых данных...")
        # Удаляем старые тестовые данные
        connection.execute(text("DELETE FROM messages WHERE chat_id IN (-1001111111111, -1001111111112, -1001111111113, -1001111111114, -1001111111115)"))
        connection.execute(text("DELETE FROM chats WHERE id IN (-1001111111111, -1001111111112, -1001111111113, -1001111111114, -1001111111115)"))
        connection.execute(text("DELETE FROM team_members WHERE user_id IN (100001, 100002, 100003)"))
        
        print("Создание тестовых чатов...")
        # Создаем чаты
        for chat_data in TEST_CHATS:
            connection.execute(text("""
                INSERT INTO chats (id, title, chat_type, is_active, created_at, updated_at)
                VALUES (:id, :title, :chat_type, :is_active, :created_at, :updated_at)
            """), {
                "id": chat_data["id"],
                "title": chat_data["title"],
                "chat_type": chat_data["chat_type"],
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
        
        print("Создание команды сотрудников...")
        # Создаем команду сотрудников
        for member_data in TEAM_MEMBERS:
            connection.execute(text("""
                INSERT INTO team_members (user_id, username, full_name, role, is_active, is_linked, created_at, updated_at)
                VALUES (:user_id, :username, :full_name, :role, :is_active, :is_linked, :created_at, :updated_at)
            """), {
                "user_id": member_data["user_id"],
                "username": member_data["username"],
                "full_name": member_data["full_name"],
                "role": member_data["role"],
                "is_active": True,
                "is_linked": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
        
        print("Создание сообщений...")
        now = datetime.utcnow()
        
        # Подготавливаем данные для пакетной вставки
        messages_data = []
        
        for i, (chat_data, clients) in enumerate(zip(TEST_CHATS, CLIENT_PROFILES)):
            chat_id = chat_data["id"]
            print(f"Подготавливаем сообщения для чата: {chat_data['title']}")
            
            # Генерируем сообщения за последние 7 дней
            for day_offset in range(7):
                message_date = now - timedelta(days=day_offset)
                
                # Количество сообщений в день (от 3 до 10)
                daily_messages = random.randint(3, 10)
                
                for msg_num in range(daily_messages):
                    # Время сообщения в течение дня (рабочие часы 9-18)
                    hour = random.randint(9, 18)
                    minute = random.randint(0, 59)
                    
                    msg_timestamp = message_date.replace(hour=hour, minute=minute, second=random.randint(0, 59))
                    
                    # Определяем отправителя (60% клиенты, 40% команда)
                    is_team_member = random.random() < 0.4
                    
                    if is_team_member:
                        # Сообщение от команды
                        team_member = random.choice(TEAM_MEMBERS)
                        user_id = team_member["user_id"]
                        username = team_member["username"]
                        full_name = team_member["full_name"]
                        message_text = random.choice(TEAM_MESSAGES)
                    else:
                        # Сообщение от клиента
                        client = random.choice(clients)
                        user_id = client["user_id"]
                        username = client["username"]
                        full_name = client["full_name"]
                        message_text = random.choice(CLIENT_MESSAGES)
                    
                    # Добавляем сообщение в список для пакетной вставки
                    messages_data.append({
                        "message_id": random.randint(1000000, 9999999),
                        "chat_id": chat_id,
                        "user_id": user_id,
                        "username": username,
                        "full_name": full_name,
                        "text": message_text,
                        "message_type": 'text',
                        "is_team_member": is_team_member,
                        "timestamp": msg_timestamp,
                        "created_at": datetime.utcnow()
                    })
        
        # Пакетная вставка сообщений
        print(f"Вставляем {len(messages_data)} сообщений...")
        connection.execute(text("""
            INSERT INTO messages (message_id, chat_id, user_id, username, full_name, text, 
                                message_type, is_team_member, timestamp, created_at)
            VALUES (:message_id, :chat_id, :user_id, :username, :full_name, :text,
                    :message_type, :is_team_member, :timestamp, :created_at)
        """), messages_data)
        
        trans.commit()
        print("Тестовые данные успешно созданы!")
        
        # Статистика
        total_messages = connection.execute(text("SELECT COUNT(*) FROM messages")).scalar()
        total_chats = connection.execute(text("SELECT COUNT(*) FROM chats")).scalar()
        total_team = connection.execute(text("SELECT COUNT(*) FROM team_members")).scalar()
        
        print(f"\nСтатистика:")
        print(f"Всего чатов: {total_chats}")
        print(f"Всего сообщений: {total_messages}")
        print(f"Членов команды: {total_team}")
        
    except Exception as e:
        trans.rollback()
        print(f"Ошибка при создании тестовых данных: {e}")
        raise
    finally:
        connection.close()

if __name__ == "__main__":
    create_test_data()