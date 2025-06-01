from datetime import datetime
from app import db
from sqlalchemy import Index


class Chat(db.Model):
    """Represents a Telegram chat/group being monitored"""
    __tablename__ = 'chats'
    
    id = db.Column(db.BigInteger, primary_key=True)  # Telegram chat ID
    title = db.Column(db.String(255), nullable=False)
    chat_type = db.Column(db.String(50), nullable=False)  # group, supergroup
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('Message', backref='chat', lazy='dynamic')
    kpis = db.relationship('KpiLive', backref='chat', lazy='dynamic')


class Message(db.Model):
    """Represents a message in a monitored chat"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.BigInteger, nullable=False)  # Telegram message ID
    chat_id = db.Column(db.BigInteger, db.ForeignKey('chats.id'), nullable=False)
    user_id = db.Column(db.BigInteger, nullable=False)  # Telegram user ID
    username = db.Column(db.String(255))
    full_name = db.Column(db.String(255))
    text = db.Column(db.Text)
    message_type = db.Column(db.String(50), default='text')  # text, photo, document, etc.
    is_team_member = db.Column(db.Boolean, nullable=False)  # True if sender is team member
    timestamp = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Sentiment analysis results
    sentiment_score = db.Column(db.Float)  # -1 to 1 scale
    sentiment_label = db.Column(db.String(20))  # positive, negative, neutral
    sentiment_confidence = db.Column(db.Float)  # 0 to 1
    processed_for_sentiment = db.Column(db.Boolean, default=False)
    
    # Response tracking
    response_time_seconds = db.Column(db.Integer)  # Time to response in seconds
    is_answered = db.Column(db.Boolean, default=False)
    
    # Create indexes for better query performance
    __table_args__ = (
        Index('idx_chat_timestamp', 'chat_id', 'timestamp'),
        Index('idx_chat_team_timestamp', 'chat_id', 'is_team_member', 'timestamp'),
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
    )


class KpiLive(db.Model):
    """Live KPI metrics calculated every 5 minutes"""
    __tablename__ = 'kpi_live'
    
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.BigInteger, db.ForeignKey('chats.id'), nullable=False)
    calculated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    
    # Enhanced response time metrics
    avg_response_time_seconds = db.Column(db.Integer)
    max_response_time_seconds = db.Column(db.Integer)
    min_response_time_seconds = db.Column(db.Integer)
    median_response_time_seconds = db.Column(db.Integer)
    p75_response_time_seconds = db.Column(db.Integer)
    p90_response_time_seconds = db.Column(db.Integer)
    p95_response_time_seconds = db.Column(db.Integer)
    
    # Response time in minutes for easy display
    avg_response_time_minutes = db.Column(db.Float)
    max_response_time_minutes = db.Column(db.Float)
    min_response_time_minutes = db.Column(db.Float)
    median_response_time_minutes = db.Column(db.Float)
    
    # Response distribution metrics
    total_responses = db.Column(db.Integer, default=0)
    responses_under_5min = db.Column(db.Integer, default=0)
    responses_under_15min = db.Column(db.Integer, default=0)
    responses_under_1hour = db.Column(db.Integer, default=0)
    responses_over_1hour = db.Column(db.Integer, default=0)
    percentage_under_5min = db.Column(db.Float, default=0.0)
    percentage_under_15min = db.Column(db.Float, default=0.0)
    percentage_under_1hour = db.Column(db.Float, default=0.0)
    percentage_over_1hour = db.Column(db.Float, default=0.0)
    
    # Message distribution
    total_messages = db.Column(db.Integer, default=0)
    client_messages = db.Column(db.Integer, default=0)
    team_messages = db.Column(db.Integer, default=0)
    unanswered_messages = db.Column(db.Integer, default=0)
    unanswered_percentage = db.Column(db.Float, default=0.0)
    
    # Sentiment distribution
    positive_messages = db.Column(db.Integer, default=0)
    negative_messages = db.Column(db.Integer, default=0)
    neutral_messages = db.Column(db.Integer, default=0)
    avg_sentiment_score = db.Column(db.Float)
    
    # Attention flags
    needs_attention = db.Column(db.Boolean, default=False)
    attention_reasons = db.Column(db.JSON)  # Array of reasons why attention is needed
    
    # Create indexes
    __table_args__ = (
        Index('idx_chat_calculated_at', 'chat_id', 'calculated_at'),
        Index('idx_calculated_at', 'calculated_at'),
        Index('idx_needs_attention', 'needs_attention'),
    )


class TeamMember(db.Model):
    """Team members configuration"""
    __tablename__ = 'team_members'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, unique=True, nullable=False)  # Telegram user ID
    username = db.Column(db.String(255))
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SystemConfig(db.Model):
    """System configuration settings"""
    __tablename__ = 'system_config'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
