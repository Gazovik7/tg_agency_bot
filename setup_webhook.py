#!/usr/bin/env python3
"""
Настройка веб-хука для Telegram бота
"""
import requests
import os

def setup_telegram_webhook():
    """Настройка веб-хука для Telegram бота"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        return False
    
    # URL веб-хука (замените на ваш домен Replit)
    webhook_url = "https://your-repl-name.your-username.replit.app/webhook/telegram"
    
    # Настройка веб-хука
    set_webhook_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    
    payload = {
        'url': webhook_url,
        'allowed_updates': ['message']
    }
    
    try:
        response = requests.post(set_webhook_url, json=payload)
        result = response.json()
        
        if result.get('ok'):
            print(f"Веб-хук успешно настроен на: {webhook_url}")
            return True
        else:
            print(f"Ошибка настройки веб-хука: {result.get('description')}")
            return False
            
    except Exception as e:
        print(f"Ошибка при настройке веб-хука: {e}")
        return False

def get_webhook_info():
    """Получение информации о текущем веб-хуке"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("TELEGRAM_BOT_TOKEN не найден")
        return
    
    info_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    try:
        response = requests.get(info_url)
        result = response.json()
        
        if result.get('ok'):
            webhook_info = result.get('result', {})
            print("Информация о веб-хуке:")
            print(f"URL: {webhook_info.get('url', 'Не установлен')}")
            print(f"Последняя ошибка: {webhook_info.get('last_error_message', 'Нет')}")
            print(f"Количество ошибок: {webhook_info.get('last_error_date', 'Нет')}")
        else:
            print(f"Ошибка получения информации: {result.get('description')}")
            
    except Exception as e:
        print(f"Ошибка: {e}")

def delete_webhook():
    """Удаление веб-хука (возврат к polling)"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("TELEGRAM_BOT_TOKEN не найден")
        return False
    
    delete_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
    
    try:
        response = requests.post(delete_url)
        result = response.json()
        
        if result.get('ok'):
            print("Веб-хук успешно удален")
            return True
        else:
            print(f"Ошибка удаления веб-хука: {result.get('description')}")
            return False
            
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

if __name__ == "__main__":
    print("1. Получить информацию о веб-хуке")
    print("2. Настроить веб-хук")
    print("3. Удалить веб-хук")
    
    choice = input("Выберите действие (1-3): ").strip()
    
    if choice == "1":
        get_webhook_info()
    elif choice == "2":
        setup_telegram_webhook()
    elif choice == "3":
        delete_webhook()
    else:
        print("Неверный выбор")