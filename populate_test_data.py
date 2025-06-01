#!/usr/bin/env python3
"""
Скрипт для заполнения базы данных тестовыми данными
Создает 10 клиентских чатов с реалистичной коммуникацией
"""

import os
import sys
from datetime import datetime, timedelta
import random
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pytz

# Настройка подключения к базе данных
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("Ошибка: переменная DATABASE_URL не установлена")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Московский часовой пояс
moscow_tz = pytz.timezone('Europe/Moscow')

# Данные для тестовых чатов
TEST_CHATS = [
    {"id": -1001111111111, "title": "Веб-разработка для ООО Альфа", "chat_type": "supergroup"},
    {"id": -1001111111112, "title": "Мобильное приложение для ИП Петров", "chat_type": "supergroup"},
    {"id": -1001111111113, "title": "Интернет-магазин для Бета Трейд", "chat_type": "supergroup"},
    {"id": -1001111111114, "title": "CRM система для Гамма Консалтинг", "chat_type": "supergroup"},
    {"id": -1001111111115, "title": "Лендинг для стартапа TechVision", "chat_type": "supergroup"},
    {"id": -1001111111116, "title": "Редизайн сайта для клиники Здоровье", "chat_type": "supergroup"},
    {"id": -1001111111117, "title": "Автоматизация для ресторана Вкусно", "chat_type": "supergroup"},
    {"id": -1001111111118, "title": "Образовательная платформа для УЦ Знание", "chat_type": "supergroup"},
    {"id": -1001111111119, "title": "Маркетплейс для Дельта Групп", "chat_type": "supergroup"},
    {"id": -1001111111120, "title": "BI аналитика для Эпсилон Банк", "chat_type": "supergroup"},
]

# Команда сотрудников
TEAM_MEMBERS = [
    {"user_id": 100001, "username": "project_manager", "full_name": "Анна Проектова", "role": "Project Manager"},
    {"user_id": 100002, "username": "senior_dev", "full_name": "Максим Разработкин", "role": "Senior Developer"},
    {"user_id": 100003, "username": "frontend_dev", "full_name": "Елена Фронтендова", "role": "Frontend Developer"},
    {"user_id": 100004, "username": "designer", "full_name": "Дмитрий Дизайнеров", "role": "UI/UX Designer"},
    {"user_id": 100005, "username": "qa_engineer", "full_name": "Ольга Тестировщикова", "role": "QA Engineer"},
]

# Клиенты для каждого чата
CLIENT_PROFILES = [
    [{"user_id": 200001, "username": "alfa_ceo", "full_name": "Иван Альфин"}, 
     {"user_id": 200002, "username": "alfa_tech", "full_name": "Петр Технический"}],
    [{"user_id": 200003, "username": "petrov_ip", "full_name": "Сергей Петров"}],
    [{"user_id": 200004, "username": "beta_owner", "full_name": "Мария Бетина"}, 
     {"user_id": 200005, "username": "beta_manager", "full_name": "Олег Менеджеров"}],
    [{"user_id": 200006, "username": "gamma_director", "full_name": "Алексей Гаммин"}],
    [{"user_id": 200007, "username": "tech_founder", "full_name": "Анастасия Визионова"}],
    [{"user_id": 200008, "username": "clinic_admin", "full_name": "Доктор Здоровеева"}],
    [{"user_id": 200009, "username": "restaurant_chef", "full_name": "Шеф Вкуснов"}],
    [{"user_id": 200010, "username": "education_head", "full_name": "Профессор Знаниев"}, 
     {"user_id": 200011, "username": "education_coord", "full_name": "Координатор Курсов"}],
    [{"user_id": 200012, "username": "delta_cto", "full_name": "CTO Дельтин"}],
    [{"user_id": 200013, "username": "bank_analyst", "full_name": "Главный Аналитик Эпсилонов"}],
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
    "Все выглядит хорошо, продолжайте",
    "Нужно ускорить разработку",
    "Отлично! Именно то, что нужно",
    "Есть проблемы с загрузкой",
    "Можно добавить эту функцию?",
    "Когда будет тестирование?",
    "Супер! Клиенты будут довольны",
    "Нужна встреча по проекту",
    "Все работает как надо",
    "Есть идеи по улучшению",
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
    "Спасибо за обратную связь!",
    "Понимаем, ускоряем темп работы",
    "Отлично, что все устраивает!",
    "Исправим проблему в течение дня",
    "Рассмотрим возможность добавления",
    "Тестирование начнем на следующей неделе",
    "Рады, что результат вас радует!",
    "Организуем встречу на завтра",
    "Отлично! Продолжаем в том же духе",
    "Отличные идеи, внедрим их",
    "Статус проекта: все идет по плану",
    "Обновил дизайн, посмотрите пожалуйста",
    "Исправил баги, можете протестировать",
    "Деплой запланирован на завтра",
    "Готов код-ревью, все прошло успешно",
]

def create_test_data():
    """Создание тестовых данных"""
    connection = engine.connect()
    trans = connection.begin()
    
    try:
        print("Создание тестовых чатов...")
        
        # Создаем чаты
        for chat_data in TEST_CHATS:
            # Проверяем существование чата
            result = connection.execute(text("SELECT id FROM chats WHERE id = :chat_id"), {"chat_id": chat_data["id"]})
            if not result.fetchone():
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
        
        # Создаем команду сотрудников
        print("Создание команды сотрудников...")
        for member_data in TEAM_MEMBERS:
            # Проверяем существование сотрудника
            result = connection.execute(text("SELECT user_id FROM team_members WHERE user_id = :user_id"), {"user_id": member_data["user_id"]})
            if not result.fetchone():
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
        
        # Создаем сообщения для каждого чата
        print("Создание сообщений...")
        
        now = datetime.utcnow()
        
        for i, (chat_data, clients) in enumerate(zip(TEST_CHATS, CLIENT_PROFILES)):
            chat_id = chat_data["id"]
            print(f"Заполняем чат: {chat_data['title']}")
            
            # Генерируем сообщения за последние 7 дней
            for day_offset in range(7):
                message_date = now - timedelta(days=day_offset)
                
                # Количество сообщений в день (от 2 до 8)
                daily_messages = random.randint(2, 8)
                
                for msg_num in range(daily_messages):
                    # Время сообщения в течение дня (рабочие часы 9-18)
                    hour = random.randint(9, 18)
                    minute = random.randint(0, 59)
                    
                    msg_timestamp = message_date.replace(hour=hour, minute=minute, second=random.randint(0, 59))
                    
                    # Определяем отправителя (70% клиенты, 30% команда)
                    is_team_member = random.random() < 0.3
                    
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
                    
                    # Создаем сообщение
                    connection.execute(text("""
                        INSERT INTO messages (message_id, chat_id, user_id, username, full_name, text, 
                                            message_type, is_team_member, timestamp, created_at)
                        VALUES (:message_id, :chat_id, :user_id, :username, :full_name, :text,
                                :message_type, :is_team_member, :timestamp, :created_at)
                    """), {
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
        
        trans.commit()
        print("Тестовые данные успешно созданы!")
        
        # Статистика
        total_messages = connection.execute(text("SELECT COUNT(*) FROM messages")).scalar()
        total_chats = connection.execute(text("SELECT COUNT(*) FROM chats")).scalar()
        total_team = connection.execute(text("SELECT COUNT(*) FROM team_members")).scalar()
        
        print(f"\nСтатистика:")
        print(f"Создано чатов: {total_chats}")
        print(f"Создано сообщений: {total_messages}")
        print(f"Членов команды: {total_team}")
        
    except Exception as e:
        trans.rollback()
        print(f"Ошибка при создании тестовых данных: {e}")
        raise
    finally:
        connection.close()

if __name__ == "__main__":
    create_test_data()