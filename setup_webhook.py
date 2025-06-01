#!/usr/bin/env python3
"""
Setup Telegram webhook
"""
import os
import requests

def setup_webhook():
    """Setup Telegram webhook"""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        print("TELEGRAM_BOT_TOKEN not found")
        return False
    
    # Get the webhook URL (Replit domain)
    webhook_url = "https://workspace.ivan-test-user-7.repl.co/telegram/webhook"
    
    # Setup webhook
    url = f"https://api.telegram.org/bot{token}/setWebhook"
    data = {
        'url': webhook_url,
        'allowed_updates': ['message']
    }
    
    response = requests.post(url, json=data)
    result = response.json()
    
    if result.get('ok'):
        print(f"Webhook set successfully to: {webhook_url}")
        return True
    else:
        print(f"Error setting webhook: {result}")
        return False

def get_webhook_info():
    """Get current webhook info"""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        print("TELEGRAM_BOT_TOKEN not found")
        return
    
    url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    response = requests.get(url)
    result = response.json()
    
    if result.get('ok'):
        info = result.get('result', {})
        print(f"Current webhook URL: {info.get('url', 'Not set')}")
        print(f"Pending updates: {info.get('pending_update_count', 0)}")
        print(f"Last error: {info.get('last_error_message', 'None')}")
    else:
        print(f"Error getting webhook info: {result}")

if __name__ == "__main__":
    print("Setting up Telegram webhook...")
    setup_webhook()
    print("\nCurrent webhook info:")
    get_webhook_info()