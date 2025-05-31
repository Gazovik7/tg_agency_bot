#!/usr/bin/env python3
"""
Check recent messages in database
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def check_messages():
    """Check recent messages"""
    session = Session()
    try:
        # Get recent messages
        result = session.execute(text("""
            SELECT 
                m.full_name,
                m.text,
                m.is_team_member,
                c.title,
                m.timestamp
            FROM messages m
            JOIN chats c ON m.chat_id = c.id
            ORDER BY m.timestamp DESC
            LIMIT 10
        """))
        
        messages = result.fetchall()
        
        print(f"Найдено сообщений в базе: {len(messages)}")
        print("-" * 50)
        
        for msg in messages:
            role = "Команда" if msg.is_team_member else "Клиент"
            print(f"[{role}] {msg.full_name} в '{msg.title}':")
            print(f"  {msg.text}")
            print(f"  Время: {msg.timestamp}")
            print()
            
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_messages()