import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import aioredis
from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker

from app import db
from models import Chat, Message, KpiLive, TeamMember
from sentiment_analyzer import SentimentAnalyzer
from kpi_calculator import KpiCalculator
from config_manager import ConfigManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageWorker:
    """Background worker for processing messages and calculating KPIs"""
    
    def __init__(self):
        self.redis = None
        self.sentiment_analyzer = SentimentAnalyzer()
        self.kpi_calculator = KpiCalculator()
        self.config = ConfigManager()
        
        # Setup database connection
        database_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/monitoring_db")
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    async def init_redis(self):
        """Initialize Redis connection"""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = aioredis.from_url(redis_url, decode_responses=True)
    
    async def start_worker(self):
        """Start the background worker"""
        await self.init_redis()
        logger.info("Starting message worker...")
        
        # Start concurrent tasks
        tasks = [
            self.process_messages(),
            self.calculate_kpis_periodically(),
            self.update_sentiment_analysis()
        ]
        
        await asyncio.gather(*tasks)
    
    async def process_messages(self):
        """Process messages from Redis queue"""
        logger.info("Starting message processor...")
        
        while True:
            try:
                # Get message from queue (blocking with timeout)
                message_data = await self.redis.brpop("message_queue", timeout=1)
                
                if message_data:
                    _, message_json = message_data
                    message_dict = json.loads(message_json)
                    await self.save_message_to_db(message_dict)
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await asyncio.sleep(1)
    
    async def save_message_to_db(self, message_data: Dict):
        """Save message to database"""
        try:
            with self.SessionLocal() as session:
                # Ensure chat exists
                chat = session.query(Chat).filter_by(id=message_data["chat_id"]).first()
                if not chat:
                    chat = Chat(
                        id=message_data["chat_id"],
                        title=message_data["chat_title"],
                        chat_type=message_data["chat_type"]
                    )
                    session.add(chat)
                    session.commit()
                
                # Check if message already exists (idempotent processing)
                existing_message = session.query(Message).filter_by(
                    message_id=message_data["message_id"],
                    chat_id=message_data["chat_id"]
                ).first()
                
                if existing_message:
                    logger.debug(f"Message {message_data['message_id']} already exists, skipping")
                    return
                
                # Create new message
                message = Message(
                    message_id=message_data["message_id"],
                    chat_id=message_data["chat_id"],
                    user_id=message_data["user_id"],
                    username=message_data.get("username"),
                    full_name=message_data.get("full_name"),
                    text=message_data.get("text", ""),
                    message_type=message_data.get("message_type", "text"),
                    is_team_member=message_data["is_team_member"],
                    timestamp=datetime.fromisoformat(message_data["timestamp"].replace('Z', '+00:00'))
                )
                
                session.add(message)
                session.commit()
                
                logger.info(f"Saved message {message_data['message_id']} from chat {message_data['chat_id']}")
                
                # Calculate response time if this is a team response
                if message_data["is_team_member"]:
                    await self.calculate_response_time(session, message)
                
        except Exception as e:
            logger.error(f"Error saving message to database: {e}")
    
    async def calculate_response_time(self, session, team_message: Message):
        """Calculate response time for team messages"""
        try:
            # Find the most recent client message before this team message
            client_message = session.query(Message).filter(
                Message.chat_id == team_message.chat_id,
                Message.is_team_member == False,
                Message.timestamp < team_message.timestamp,
                Message.is_answered == False
            ).order_by(desc(Message.timestamp)).first()
            
            if client_message:
                # Calculate response time
                response_time = (team_message.timestamp - client_message.timestamp).total_seconds()
                team_message.response_time_seconds = int(response_time)
                
                # Mark client message as answered
                client_message.is_answered = True
                client_message.response_time_seconds = int(response_time)
                
                session.commit()
                
                logger.debug(f"Calculated response time: {response_time} seconds for message {team_message.message_id}")
        
        except Exception as e:
            logger.error(f"Error calculating response time: {e}")
    
    async def calculate_kpis_periodically(self):
        """Calculate KPIs every 5 minutes"""
        logger.info("Starting KPI calculator...")
        
        while True:
            try:
                await asyncio.sleep(300)  # 5 minutes
                await self.calculate_kpis()
            except Exception as e:
                logger.error(f"Error in KPI calculation: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def calculate_kpis(self):
        """Calculate KPIs for all active chats"""
        try:
            with self.SessionLocal() as session:
                # Get all active chats
                chats = session.query(Chat).filter_by(is_active=True).all()
                
                for chat in chats:
                    await self.calculate_chat_kpis(session, chat)
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Error calculating KPIs: {e}")
    
    async def calculate_chat_kpis(self, session, chat: Chat):
        """Calculate KPIs for a specific chat"""
        try:
            # Calculate KPIs for the last 24 hours
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            
            kpis = self.kpi_calculator.calculate_chat_kpis(session, chat.id, start_time, end_time)
            
            if kpis:
                # Check if KPI record for this period already exists
                existing_kpi = session.query(KpiLive).filter(
                    KpiLive.chat_id == chat.id,
                    KpiLive.period_start == start_time,
                    KpiLive.period_end == end_time
                ).first()
                
                if existing_kpi:
                    # Update existing record
                    for key, value in kpis.items():
                        setattr(existing_kpi, key, value)
                    existing_kpi.calculated_at = datetime.utcnow()
                else:
                    # Create new KPI record
                    kpi_record = KpiLive(
                        chat_id=chat.id,
                        period_start=start_time,
                        period_end=end_time,
                        **kpis
                    )
                    session.add(kpi_record)
                
                logger.debug(f"Calculated KPIs for chat {chat.id}")
        
        except Exception as e:
            logger.error(f"Error calculating KPIs for chat {chat.id}: {e}")
    
    async def update_sentiment_analysis(self):
        """Update sentiment analysis for messages that haven't been processed"""
        logger.info("Starting sentiment analysis updater...")
        
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self.process_sentiment_analysis()
            except Exception as e:
                logger.error(f"Error in sentiment analysis: {e}")
                await asyncio.sleep(60)
    
    async def process_sentiment_analysis(self):
        """Process sentiment analysis for unprocessed messages"""
        try:
            with self.SessionLocal() as session:
                # Get unprocessed messages with text content
                messages = session.query(Message).filter(
                    Message.processed_for_sentiment == False,
                    Message.text.isnot(None),
                    Message.text != ""
                ).limit(10).all()  # Process 10 messages at a time
                
                for message in messages:
                    sentiment_result = await self.sentiment_analyzer.analyze_sentiment(message.text)
                    
                    if sentiment_result:
                        message.sentiment_score = sentiment_result.get("score")
                        message.sentiment_label = sentiment_result.get("label")
                        message.sentiment_confidence = sentiment_result.get("confidence")
                    
                    message.processed_for_sentiment = True
                
                if messages:
                    session.commit()
                    logger.info(f"Processed sentiment analysis for {len(messages)} messages")
        
        except Exception as e:
            logger.error(f"Error processing sentiment analysis: {e}")


async def main():
    """Main function to run the worker"""
    worker = MessageWorker()
    try:
        await worker.start_worker()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker crashed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
