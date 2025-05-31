import logging
import json
from datetime import datetime, timedelta
from flask import request, jsonify, render_template, redirect, url_for, flash
from sqlalchemy import desc, func
from sqlalchemy.orm import sessionmaker

from app import app, db
from models import Chat, Message, KpiLive, TeamMember, SystemConfig
from config_manager import ConfigManager
from kpi_calculator import KpiCalculator
from timezone_utils import utc_to_configured_timezone, format_configured_time, now_in_configured_timezone

logger = logging.getLogger(__name__)

# Initialize components
config_manager = ConfigManager()
kpi_calculator = KpiCalculator()


def verify_admin_token():
    """Verify admin token from request headers"""
    # Check both Authorization header and X-Admin-Token header
    auth_header = request.headers.get('Authorization', '')
    admin_token_header = request.headers.get('X-Admin-Token', '')
    
    token = None
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]  # Remove 'Bearer ' prefix
    elif admin_token_header:
        token = admin_token_header
    
    if not token:
        return False
    
    # Get token from environment variable first, then config file
    import os
    expected_token = os.getenv("ADMIN_TOKEN") or config_manager.get_api_config().get("admin_token")
    return token == expected_token


@app.route('/')
def index():
    """Main dashboard page"""
    import os
    admin_token = os.getenv("ADMIN_TOKEN")
    return render_template('dashboard.html', admin_token=admin_token)


@app.route('/dashboard-data')
def dashboard_data():
    """API endpoint for dashboard data"""
    
    # Verify admin token
    if not verify_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # Проверяем новые сообщения Telegram перед обновлением дашборда
        try:
            from telegram_updater import update_telegram_messages
            new_messages = update_telegram_messages()
            if new_messages > 0:
                logger.info(f"Получено {new_messages} новых сообщений")
        except Exception as e:
            logger.error(f"Ошибка обновления Telegram сообщений: {e}")
        
        hours = request.args.get('hours', 24, type=int)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Get summary statistics
        summary = kpi_calculator.get_dashboard_summary(db.session, hours)
        
        # Get chats needing attention
        attention_chats = get_chats_needing_attention()
        
        # Get activity data
        activity_data = get_activity_data(start_time, end_time)
        
        # Get sentiment data
        sentiment_data = get_sentiment_data(start_time, end_time)
        
        # Get team performance
        team_performance = get_team_performance(start_time, end_time)
        
        # Get client statistics
        client_stats = get_client_statistics(start_time, end_time)
        
        dashboard_response = {
            "summary": summary,
            "attention_chats": attention_chats,
            "activity": activity_data,
            "sentiment": sentiment_data,
            "team_performance": team_performance,
            "client_stats": client_stats,
            "last_updated": format_configured_time(datetime.utcnow(), '%Y-%m-%d %H:%M:%S'),
            "period": {
                "start": format_configured_time(start_time, '%Y-%m-%d %H:%M:%S'),
                "end": format_configured_time(end_time, '%Y-%m-%d %H:%M:%S'),
                "hours": hours
            }
        }
        
        return jsonify(dashboard_response)
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return jsonify({"error": "Internal server error"}), 500


def get_chats_needing_attention():
    """Get chats that need attention"""
    try:
        # Get latest KPIs for chats needing attention
        attention_kpis = db.session.query(KpiLive).filter(
            KpiLive.needs_attention == True
        ).order_by(desc(KpiLive.calculated_at)).limit(20).all()
        
        chats_attention = []
        for kpi in attention_kpis:
            chat = db.session.query(Chat).filter_by(id=kpi.chat_id).first()
            if chat:
                chats_attention.append({
                    "chat_id": chat.id,
                    "chat_title": chat.title,
                    "reasons": kpi.attention_reasons,
                    "avg_response_time": kpi.avg_response_time_seconds,
                    "unanswered_percentage": kpi.unanswered_percentage,
                    "negative_messages": kpi.negative_messages,
                    "last_calculated": format_configured_time(kpi.calculated_at) or kpi.calculated_at.isoformat()
                })
        
        return chats_attention
        
    except Exception as e:
        logger.error(f"Error getting attention chats: {e}")
        return []


def get_activity_data(start_time, end_time):
    """Get activity data for charts"""
    try:
        # Hourly message counts
        hourly_data = db.session.query(
            func.date_trunc('hour', Message.timestamp).label('hour'),
            func.count(Message.id).label('total_messages'),
            func.sum(func.cast(~Message.is_team_member, db.Integer)).label('client_messages'),
            func.sum(func.cast(Message.is_team_member, db.Integer)).label('team_messages')
        ).filter(
            Message.timestamp >= start_time,
            Message.timestamp <= end_time
        ).group_by('hour').order_by('hour').all()
        
        activity_chart = {
            "labels": [format_configured_time(row.hour, '%H:00') or row.hour.strftime('%H:00') for row in hourly_data],
            "datasets": [
                {
                    "label": "Client Messages",
                    "data": [row.client_messages for row in hourly_data],
                    "backgroundColor": "rgba(54, 162, 235, 0.6)"
                },
                {
                    "label": "Team Messages", 
                    "data": [row.team_messages for row in hourly_data],
                    "backgroundColor": "rgba(75, 192, 192, 0.6)"
                }
            ]
        }
        
        return {
            "hourly_chart": activity_chart,
            "total_messages": sum(row.total_messages for row in hourly_data),
            "client_messages": sum(row.client_messages for row in hourly_data),
            "team_messages": sum(row.team_messages for row in hourly_data)
        }
        
    except Exception as e:
        logger.error(f"Error getting activity data: {e}")
        return {"hourly_chart": {"labels": [], "datasets": []}}


def get_sentiment_data(start_time, end_time):
    """Get sentiment analysis data"""
    try:
        # Sentiment distribution
        sentiment_counts = db.session.query(
            Message.sentiment_label,
            func.count(Message.id).label('count')
        ).filter(
            Message.timestamp >= start_time,
            Message.timestamp <= end_time,
            Message.sentiment_label.isnot(None)
        ).group_by(Message.sentiment_label).all()
        
        sentiment_chart = {
            "labels": [row.sentiment_label.title() for row in sentiment_counts],
            "data": [row.count for row in sentiment_counts],
            "backgroundColor": [
                "rgba(75, 192, 192, 0.6)" if label == "positive" else
                "rgba(255, 99, 132, 0.6)" if label == "negative" else
                "rgba(255, 205, 86, 0.6)"
                for label in [row.sentiment_label for row in sentiment_counts]
            ]
        }
        
        # Average sentiment over time
        daily_sentiment = db.session.query(
            func.date(Message.timestamp).label('date'),
            func.avg(Message.sentiment_score).label('avg_sentiment')
        ).filter(
            Message.timestamp >= start_time,
            Message.timestamp <= end_time,
            Message.sentiment_score.isnot(None)
        ).group_by('date').order_by('date').all()
        
        sentiment_trend = {
            "labels": [row.date.strftime('%m/%d') for row in daily_sentiment],
            "data": [float(row.avg_sentiment) if row.avg_sentiment else 0 for row in daily_sentiment]
        }
        
        return {
            "distribution_chart": sentiment_chart,
            "trend_chart": sentiment_trend,
            "total_analyzed": sum(row.count for row in sentiment_counts)
        }
        
    except Exception as e:
        logger.error(f"Error getting sentiment data: {e}")
        return {"distribution_chart": {"labels": [], "data": []}, "trend_chart": {"labels": [], "data": []}}


def get_team_performance(start_time, end_time):
    """Get team member performance data"""
    try:
        team_members = config_manager.get_team_members()
        
        performance_data = []
        if team_members:
            for user_id, member_info in team_members.items():
                user_id = int(user_id) if isinstance(user_id, str) else user_id
                
                # Get team member's messages and response times
                member_stats = db.session.query(
                    func.count(Message.id).label('message_count'),
                    func.avg(Message.response_time_seconds).label('avg_response_time'),
                    func.min(Message.response_time_seconds).label('min_response_time'),
                    func.max(Message.response_time_seconds).label('max_response_time')
                ).filter(
                    Message.user_id == user_id,
                    Message.is_team_member == True,
                    Message.timestamp >= start_time,
                    Message.timestamp <= end_time
                ).first()
                
                performance_data.append({
                    "user_id": user_id,
                    "name": member_info.get("name", "Unknown"),
                    "role": member_info.get("role", "Team Member"),
                    "message_count": member_stats.message_count or 0,
                    "avg_response_time": int(member_stats.avg_response_time) if member_stats.avg_response_time else None,
                    "min_response_time": member_stats.min_response_time,
                    "max_response_time": member_stats.max_response_time
                })
        
        return performance_data
        
    except Exception as e:
        logger.error(f"Error getting team performance: {e}")
        return []


def get_client_statistics(start_time, end_time):
    """Get client statistics"""
    try:
        # Most active clients
        active_clients = db.session.query(
            Message.user_id,
            Message.full_name,
            func.count(Message.id).label('message_count'),
            func.max(Message.timestamp).label('last_message')
        ).filter(
            Message.is_team_member == False,
            Message.timestamp >= start_time,
            Message.timestamp <= end_time
        ).group_by(Message.user_id, Message.full_name).order_by(
            desc('message_count')
        ).limit(10).all()
        
        client_data = []
        for client in active_clients:
            client_data.append({
                "user_id": client.user_id,
                "name": client.full_name or "Unknown",
                "message_count": client.message_count,
                "last_message": client.last_message.isoformat()
            })
        
        return {
            "most_active": client_data,
            "total_unique_clients": len(active_clients)
        }
        
    except Exception as e:
        logger.error(f"Error getting client statistics: {e}")
        return {"most_active": [], "total_unique_clients": 0}


@app.route('/config')
def view_config():
    """View current configuration"""
    if not verify_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        config_data = config_manager.get_config()
        env_vars = config_manager.get_environment_variables()
        validation_issues = config_manager.validate_configuration()
        
        return jsonify({
            "config": config_data,
            "environment": {k: "***SET***" if v else "NOT SET" for k, v in env_vars.items()},
            "validation": validation_issues
        })
        
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/config', methods=['POST'])
def update_config():
    """Update configuration"""
    if not verify_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        new_config = request.json
        config_manager.update_config(new_config)
        return jsonify({"message": "Configuration updated successfully"})
        
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db.session.execute(db.text('SELECT 1'))
        
        # Check recent activity
        recent_messages = db.session.query(Message).filter(
            Message.timestamp >= datetime.utcnow() - timedelta(hours=1)
        ).count()
        
        # Check Redis connection (basic check)
        import redis
        redis_url = config_manager.get_environment_variables()["REDIS_URL"]
        r = redis.from_url(redis_url)
        r.ping()
        
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "recent_messages": recent_messages,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500
