"""
Telegram webhook handler for receiving messages
"""
import os
import logging
from datetime import datetime
import psycopg2
from flask import request, jsonify
from app import app

logger = logging.getLogger(__name__)

# Team members configuration
TEAM_MEMBERS = {265739915}  # Иван Смирнов

def save_telegram_message(message_data):
    """Save Telegram message to database"""
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cur = conn.cursor()
        
        # Extract message info
        message = message_data.get('message', {})
        chat = message.get('chat', {})
        user = message.get('from', {})
        
        chat_id = chat.get('id')
        chat_title = chat.get('title', 'Private Chat')
        chat_type = chat.get('type', 'private')
        
        user_id = user.get('id')
        username = user.get('username')
        first_name = user.get('first_name', '') or ''
        last_name = user.get('last_name', '') or ''
        full_name = f"{first_name} {last_name}".strip()
        
        text = message.get('text', '') or message.get('caption', '')
        message_id = message.get('message_id')
        timestamp = datetime.fromtimestamp(message.get('date', 0))
        
        is_team_member = user_id in TEAM_MEMBERS
        
        # Insert or update chat
        cur.execute("""
            INSERT INTO chats (id, title, chat_type, is_active, created_at, updated_at) 
            VALUES (%s, %s, %s, true, %s, %s)
            ON CONFLICT (id) DO UPDATE SET 
                title = EXCLUDED.title,
                updated_at = EXCLUDED.updated_at
        """, (chat_id, chat_title, chat_type, datetime.utcnow(), datetime.utcnow()))
        
        # Insert message
        cur.execute("""
            INSERT INTO messages (
                message_id, chat_id, user_id, username, full_name, text,
                message_type, is_team_member, timestamp, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, 'text', %s, %s, %s)
        """, (
            message_id, chat_id, user_id, username, full_name, text,
            is_team_member, timestamp, datetime.utcnow()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Message saved: {full_name} ({'team' if is_team_member else 'client'}) in {chat_title}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving message: {e}")
        return False

@app.route('/telegram/webhook', methods=['POST'])
def telegram_webhook():
    """Handle Telegram webhook updates"""
    try:
        data = request.get_json()
        
        if 'message' in data:
            save_telegram_message(data)
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'status': 'error'}), 500

@app.route('/telegram/status')
def telegram_status():
    """Check Telegram webhook status"""
    return jsonify({
        'status': 'active',
        'webhook_url': f"{request.host_url}telegram/webhook"
    })