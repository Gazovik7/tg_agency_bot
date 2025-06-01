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
from response_time_analyzer import ResponseTimeAnalyzer
from timezone_utils import moscow_date_to_utc_range, utc_to_moscow, format_moscow_date, get_moscow_now, format_configured_time

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


@app.route('/response-time-analysis')
def response_time_analysis_page():
    """Response time analysis page"""
    return render_template('response_time_analysis.html')


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


@app.route('/chat-management')
def chat_management():
    """Chat management page"""
    import os
    admin_token = os.getenv("ADMIN_TOKEN")
    return render_template('chat_management.html', admin_token=admin_token)


@app.route('/api/chats-management')
def api_chats_management():
    """API endpoint for chat management data"""
    if not verify_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # Получаем все чаты с участниками и статистикой
        chats_data = []
        
        chats = Chat.query.filter_by(is_active=True).all()
        
        for chat in chats:
            # Получаем уникальных участников чата
            users_query = db.session.query(
                Message.user_id,
                Message.username,
                Message.full_name,
                Message.is_team_member,
                func.count(Message.id).label('message_count'),
                func.sum(func.length(Message.text)).label('character_count')
            ).filter(
                Message.chat_id == chat.id
            ).group_by(
                Message.user_id,
                Message.username, 
                Message.full_name,
                Message.is_team_member
            ).all()
            
            users = []
            total_messages = 0
            team_messages = 0
            client_messages = 0
            
            for user in users_query:
                total_messages += user.message_count
                if user.is_team_member:
                    team_messages += user.message_count
                else:
                    client_messages += user.message_count
                
                users.append({
                    'user_id': user.user_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'is_team_member': user.is_team_member,
                    'message_count': user.message_count,
                    'character_count': user.character_count or 0
                })
            
            chats_data.append({
                'id': chat.id,
                'title': chat.title,
                'chat_type': chat.chat_type,
                'users': users,
                'stats': {
                    'total_messages': total_messages,
                    'team_messages': team_messages,
                    'client_messages': client_messages
                }
            })
        
        return jsonify({'chats': chats_data})
        
    except Exception as e:
        logger.error(f"Error getting chats management data: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/chat-users/<int:chat_id>')
def api_chat_users(chat_id):
    """Get users for specific chat"""
    if not verify_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        chat = Chat.query.get_or_404(chat_id)
        
        # Получаем участников чата
        users_query = db.session.query(
            Message.user_id,
            Message.username,
            Message.full_name,
            Message.is_team_member,
            func.count(Message.id).label('message_count')
        ).filter(
            Message.chat_id == chat_id
        ).group_by(
            Message.user_id,
            Message.username,
            Message.full_name,
            Message.is_team_member
        ).all()
        
        users = []
        for user in users_query:
            users.append({
                'user_id': user.user_id,
                'username': user.username,
                'full_name': user.full_name,
                'is_team_member': user.is_team_member,
                'message_count': user.message_count
            })
        
        return jsonify({
            'chat': {
                'id': chat.id,
                'title': chat.title
            },
            'users': users
        })
        
    except Exception as e:
        logger.error(f"Error getting chat users: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/chat-team/<int:chat_id>', methods=['POST'])
def api_update_chat_team(chat_id):
    """Update team members for specific chat"""
    if not verify_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        if not data or 'team_members' not in data:
            return jsonify({"error": "Invalid data"}), 400
        
        # Обновляем статус участников команды
        for member in data['team_members']:
            user_id = member['user_id']
            is_team_member = member['is_team_member']
            
            # Обновляем все сообщения этого пользователя в данном чате
            Message.query.filter_by(
                chat_id=chat_id,
                user_id=user_id
            ).update({'is_team_member': is_team_member})
        
        db.session.commit()
        
        return jsonify({"success": True, "message": "Team members updated successfully"})
        
    except Exception as e:
        logger.error(f"Error updating chat team: {e}")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500


@app.route('/chat-details')
def chat_details():
    """Chat details page"""
    import os
    admin_token = os.getenv("ADMIN_TOKEN")
    return render_template('chat_details.html', admin_token=admin_token)


@app.route('/api/chat-stats/<int:chat_id>')
def api_chat_detailed_stats(chat_id):
    """Get detailed statistics for specific chat"""
    if not verify_admin_token():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        chat = Chat.query.get_or_404(chat_id)
        hours = request.args.get('hours', 24, type=int)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Статистика по участникам
        users_stats = db.session.query(
            Message.user_id,
            Message.username,
            Message.full_name,
            Message.is_team_member,
            func.count(Message.id).label('message_count'),
            func.sum(func.length(Message.text)).label('character_count'),
            func.avg(func.length(Message.text)).label('avg_message_length')
        ).filter(
            Message.chat_id == chat_id,
            Message.timestamp >= start_time,
            Message.timestamp <= end_time
        ).group_by(
            Message.user_id,
            Message.username,
            Message.full_name,
            Message.is_team_member
        ).all()
        
        # Почасовая активность
        hourly_stats = db.session.query(
            func.date_trunc('hour', Message.timestamp).label('hour'),
            func.count(func.case([(Message.is_team_member == True, 1)])).label('team_messages'),
            func.count(func.case([(Message.is_team_member == False, 1)])).label('client_messages'),
            func.sum(func.case([(Message.is_team_member == True, func.length(Message.text))])).label('team_characters'),
            func.sum(func.case([(Message.is_team_member == False, func.length(Message.text))])).label('client_characters')
        ).filter(
            Message.chat_id == chat_id,
            Message.timestamp >= start_time,
            Message.timestamp <= end_time
        ).group_by('hour').order_by('hour').all()
        
        users_data = []
        team_total_messages = 0
        client_total_messages = 0
        team_total_characters = 0
        client_total_characters = 0
        
        for user in users_stats:
            user_data = {
                'user_id': user.user_id,
                'username': user.username,
                'full_name': user.full_name,
                'is_team_member': user.is_team_member,
                'message_count': user.message_count,
                'character_count': user.character_count or 0,
                'avg_message_length': round(user.avg_message_length or 0, 1)
            }
            users_data.append(user_data)
            
            if user.is_team_member:
                team_total_messages += user.message_count
                team_total_characters += user.character_count or 0
            else:
                client_total_messages += user.message_count
                client_total_characters += user.character_count or 0
        
        # Форматируем почасовые данные
        hourly_data = []
        for hour in hourly_stats:
            hourly_data.append({
                'hour': format_configured_time(hour.hour, '%H:00') if format_configured_time(hour.hour, '%H:00') else hour.hour.strftime('%H:00'),
                'team_messages': hour.team_messages or 0,
                'client_messages': hour.client_messages or 0,
                'team_characters': hour.team_characters or 0,
                'client_characters': hour.client_characters or 0
            })
        
        return jsonify({
            'chat': {
                'id': chat.id,
                'title': chat.title
            },
            'period': {
                'start': format_configured_time(start_time) or start_time.isoformat(),
                'end': format_configured_time(end_time) or end_time.isoformat(),
                'hours': hours
            },
            'summary': {
                'team_messages': team_total_messages,
                'client_messages': client_total_messages,
                'team_characters': team_total_characters,
                'client_characters': client_total_characters,
                'total_messages': team_total_messages + client_total_messages,
                'total_characters': team_total_characters + client_total_characters
            },
            'users': users_data,
            'hourly_activity': hourly_data
        })
        
    except Exception as e:
        logger.error(f"Error getting chat detailed stats: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/filtered-dashboard-data')
def filtered_dashboard_data():
    """API endpoint for filtered dashboard data"""
    try:
        # Get filter parameters
        chat_id = request.args.get('chat_id', type=int)
        employee_id = request.args.get('employee_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Default time range (last 7 days if no dates provided)
        if start_date and end_date:
            # Convert Moscow dates to UTC range
            start_time, _ = moscow_date_to_utc_range(start_date)
            _, end_time = moscow_date_to_utc_range(end_date)
        else:
            # Default to last 7 days in Moscow time
            moscow_now = get_moscow_now()
            moscow_end = moscow_now.replace(hour=23, minute=59, second=59, microsecond=999999)
            moscow_start = (moscow_now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Convert to UTC
            from timezone_utils import moscow_to_utc
            end_time = moscow_to_utc(moscow_end).replace(tzinfo=None)
            start_time = moscow_to_utc(moscow_start).replace(tzinfo=None)
        
        # Build query filters
        query_filters = [
            Message.timestamp >= start_time,
            Message.timestamp <= end_time
        ]
        
        if chat_id:
            query_filters.append(Message.chat_id == chat_id)
        
        if employee_id:
            query_filters.append(Message.user_id == employee_id)
        
        # Get filtered messages
        messages = db.session.query(Message).filter(*query_filters).all()
        
        # Debug log
        logger.info(f"Filtered messages count: {len(messages)}")
        logger.info(f"Query filters: {query_filters}")
        
        # Calculate statistics
        total_messages = len(messages)
        client_messages = len([m for m in messages if not m.is_team_member])
        team_messages = len([m for m in messages if m.is_team_member])
        total_symbols = sum(len(m.text or '') for m in messages)
        
        logger.info(f"Stats: total={total_messages}, client={client_messages}, team={team_messages}, symbols={total_symbols}")
        
        # Calculate enhanced response times using new analyzer
        analyzer = ResponseTimeAnalyzer()
        
        # Get overall response metrics for all active chats in the period
        overall_response_metrics = {
            'avg_response_time_minutes': 0,
            'max_response_time_minutes': 0,
            'median_response_time_minutes': 0,
            'total_responses': 0
        }
        
        if chat_id:
            # For specific chat, use detailed analysis
            chat_metrics = analyzer.analyze_chat_response_times(db.session, chat_id, start_time, end_time)
            overall_response_metrics = chat_metrics
        else:
            # For overall view, calculate aggregated metrics
            active_chats = db.session.query(Chat).join(Message).filter(*query_filters).distinct().all()
            all_response_times = []
            
            for chat in active_chats:
                chat_metrics = analyzer.analyze_chat_response_times(db.session, chat.id, start_time, end_time)
                if chat_metrics['total_responses'] > 0:
                    # Collect all response times for overall calculation
                    # We'll use the basic response_time_seconds from messages for aggregation
                    chat_response_times = db.session.query(Message.response_time_seconds).filter(
                        Message.chat_id == chat.id,
                        Message.timestamp >= start_time,
                        Message.timestamp <= end_time,
                        Message.response_time_seconds.isnot(None),
                        Message.response_time_seconds > 0
                    ).all()
                    all_response_times.extend([rt[0] for rt in chat_response_times])
            
            if all_response_times:
                overall_response_metrics = {
                    'avg_response_time_minutes': round(sum(all_response_times) / len(all_response_times) / 60, 1),
                    'max_response_time_minutes': round(max(all_response_times) / 60, 1),
                    'median_response_time_minutes': round(sorted(all_response_times)[len(all_response_times)//2] / 60, 1),
                    'total_responses': len(all_response_times)
                }
        
        # Get employee activity data (by individual users)
        employee_stats = db.session.query(
            Message.user_id,
            Message.full_name,
            func.count(Message.id).label('message_count'),
            func.sum(func.length(Message.text)).label('character_count')
        ).filter(*query_filters, Message.is_team_member == True).group_by(
            Message.user_id, Message.full_name
        ).all()
        
        employees_data = []
        for emp in employee_stats:
            employees_data.append({
                'user_id': emp.user_id,
                'name': emp.full_name or 'Unknown',
                'message_count': emp.message_count,
                'character_count': emp.character_count or 0
            })
        
        # Get all chats with messages in the filtered period
        active_chats = db.session.query(Chat).join(Message).filter(*query_filters).distinct().all()
        
        clients_data = []
        for chat in active_chats:
            # Get team messages for this chat
            team_stats = db.session.query(
                func.count(Message.id).label('count'),
                func.sum(func.length(Message.text)).label('characters')
            ).filter(
                Message.chat_id == chat.id,
                Message.is_team_member == True,
                *query_filters
            ).first()
            
            # Get client messages for this chat
            client_stats = db.session.query(
                func.count(Message.id).label('count'),
                func.sum(func.length(Message.text)).label('characters')
            ).filter(
                Message.chat_id == chat.id,
                Message.is_team_member == False,
                *query_filters
            ).first()
            
            chat_team_messages = team_stats.count or 0
            chat_team_characters = team_stats.characters or 0
            chat_client_messages = client_stats.count or 0
            chat_client_characters = client_stats.characters or 0
            
            chat_total_messages = chat_team_messages + chat_client_messages
            chat_total_characters = chat_team_characters + chat_client_characters
            
            if chat_total_messages > 0:
                team_message_ratio = (chat_team_messages / chat_total_messages) * 100
                client_message_ratio = (chat_client_messages / chat_total_messages) * 100
            else:
                team_message_ratio = 0
                client_message_ratio = 0
            
            if chat_total_characters > 0:
                team_char_ratio = (chat_team_characters / chat_total_characters) * 100
                client_char_ratio = (chat_client_characters / chat_total_characters) * 100
            else:
                team_char_ratio = 0
                client_char_ratio = 0
            
            if chat_total_messages > 0:  # Only include chats with messages
                # Get detailed response time metrics for this chat
                chat_response_metrics = analyzer.analyze_chat_response_times(db.session, chat.id, start_time, end_time)
                
                clients_data.append({
                    'chat_id': chat.id,
                    'name': chat.title,
                    'team_messages': chat_team_messages,
                    'client_messages': chat_client_messages,
                    'team_characters': chat_team_characters,
                    'client_characters': chat_client_characters,
                    'total_messages': chat_total_messages,
                    'total_characters': chat_total_characters,
                    'team_message_ratio': round(team_message_ratio, 1),
                    'client_message_ratio': round(client_message_ratio, 1),
                    'team_char_ratio': round(team_char_ratio, 1),
                    'client_char_ratio': round(client_char_ratio, 1),
                    'communication_intensity': chat_total_messages,  # For sorting
                    
                    # Response time metrics
                    'avg_response_time_minutes': chat_response_metrics.get('avg_response_time_minutes', 0),
                    'max_response_time_minutes': chat_response_metrics.get('max_response_time_minutes', 0),
                    'median_response_time_minutes': chat_response_metrics.get('median_response_time_minutes', 0),
                    'total_responses': chat_response_metrics.get('total_responses', 0),
                    'responses_under_5min': chat_response_metrics.get('responses_under_5min', 0),
                    'responses_over_1hour': chat_response_metrics.get('responses_over_1hour', 0),
                    'percentage_under_5min': chat_response_metrics.get('percentage_under_5min', 0),
                    'percentage_over_1hour': chat_response_metrics.get('percentage_over_1hour', 0)
                })
        
        # Sort by communication intensity
        employees_data.sort(key=lambda x: x['message_count'], reverse=True)
        clients_data.sort(key=lambda x: x['communication_intensity'], reverse=True)
        
        return jsonify({
            'general_stats': {
                'total_messages': total_messages,
                'client_messages': client_messages,
                'team_messages': team_messages,
                'total_symbols': total_symbols,
                'avg_response_time_minutes': overall_response_metrics.get('avg_response_time_minutes', 0),
                'max_response_time_minutes': overall_response_metrics.get('max_response_time_minutes', 0),
                'median_response_time_minutes': overall_response_metrics.get('median_response_time_minutes', 0),
                'total_responses': overall_response_metrics.get('total_responses', 0),
                'client_percentage': round((client_messages / total_messages * 100), 1) if total_messages else 0,
                'team_percentage': round((team_messages / total_messages * 100), 1) if total_messages else 0
            },
            'employees': employees_data,
            'clients': clients_data,
            'period': {
                'start': format_moscow_date(start_time),
                'end': format_moscow_date(end_time)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting filtered dashboard data: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/filter-options')
def filter_options():
    """Get available filter options (chats and employees)"""
    try:
        # Get active chats
        chats = db.session.query(Chat).filter_by(is_active=True).all()
        chats_data = [{'id': chat.id, 'title': chat.title} for chat in chats]
        
        # Get team members
        team_members = db.session.query(
            Message.user_id,
            Message.full_name
        ).filter(
            Message.is_team_member == True
        ).group_by(
            Message.user_id, Message.full_name
        ).all()
        
        employees_data = [
            {'id': emp.user_id, 'name': emp.full_name or 'Unknown'}
            for emp in team_members
        ]
        
        return jsonify({
            'chats': chats_data,
            'employees': employees_data
        })
        
    except Exception as e:
        logger.error(f"Error getting filter options: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/response-time-analysis')
def response_time_analysis():
    """Get detailed response time analysis"""
    try:
        verify_admin_token()
        
        # Get parameters
        chat_id = request.args.get('chat_id', type=int)
        employee_id = request.args.get('employee_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        hours = request.args.get('hours', default=24, type=int)
        
        # Initialize response time analyzer
        analyzer = ResponseTimeAnalyzer()
        
        # Determine time range
        if start_date and end_date:
            start_time, end_time = moscow_date_to_utc_range(start_date, end_date)
        else:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
        
        if chat_id:
            # Analysis for specific chat
            metrics = analyzer.analyze_chat_response_times(db.session, chat_id, start_time, end_time)
            
            # Get chat info
            chat = db.session.query(Chat).filter_by(id=chat_id).first()
            chat_title = chat.title if chat else f"Chat {chat_id}"
            
            return jsonify({
                'type': 'chat',
                'chat_id': chat_id,
                'chat_title': chat_title,
                'metrics': metrics,
                'period': {
                    'start': format_moscow_date(start_time),
                    'end': format_moscow_date(end_time)
                }
            })
            
        elif employee_id:
            # Analysis for specific employee
            metrics = analyzer.analyze_team_member_performance(db.session, employee_id, start_time, end_time)
            
            # Get employee info
            employee = db.session.query(Message.full_name).filter(
                Message.user_id == employee_id,
                Message.is_team_member == True
            ).first()
            
            employee_name = employee.full_name if employee else f"Employee {employee_id}"
            
            return jsonify({
                'type': 'employee',
                'employee_id': employee_id,
                'employee_name': employee_name,
                'metrics': metrics,
                'period': {
                    'start': format_moscow_date(start_time),
                    'end': format_moscow_date(end_time)
                }
            })
            
        else:
            # Overall analysis for all chats
            all_metrics = {
                'total_responses': 0,
                'all_response_times': [],
                'chat_analyses': []
            }
            
            # Get all active chats
            active_chats = db.session.query(Chat).filter_by(is_active=True).all()
            
            for chat in active_chats:
                chat_metrics = analyzer.analyze_chat_response_times(db.session, chat.id, start_time, end_time)
                
                if chat_metrics['total_responses'] > 0:
                    all_metrics['chat_analyses'].append({
                        'chat_id': chat.id,
                        'chat_title': chat.title,
                        'metrics': chat_metrics
                    })
                    all_metrics['total_responses'] += chat_metrics['total_responses']
            
            # Calculate overall statistics
            if all_metrics['total_responses'] > 0:
                # Collect all response times for overall calculation
                overall_response_times = []
                for chat_analysis in all_metrics['chat_analyses']:
                    # We'll need to get individual response times for overall calculation
                    # For now, use weighted averages based on chat metrics
                    pass
                
                # Sort chats by max response time
                all_metrics['chat_analyses'].sort(
                    key=lambda x: x['metrics']['max_response_time_minutes'] or 0, 
                    reverse=True
                )
            
            return jsonify({
                'type': 'overall',
                'metrics': all_metrics,
                'period': {
                    'start': format_moscow_date(start_time),
                    'end': format_moscow_date(end_time)
                }
            })
            
    except Exception as e:
        logger.error(f"Error in response time analysis: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/slow-response-alerts')
def slow_response_alerts():
    """Get alerts for slow responses"""
    try:
        verify_admin_token()
        
        hours = request.args.get('hours', default=24, type=int)
        
        # Initialize response time analyzer
        analyzer = ResponseTimeAnalyzer()
        
        # Get slow response alerts
        alerts = analyzer.get_slow_response_alerts(db.session, hours)
        
        return jsonify({
            'alerts': alerts,
            'period_hours': hours,
            'total_alerts': len(alerts),
            'critical_alerts': len([a for a in alerts if a['alert_level'] == 'critical']),
            'high_alerts': len([a for a in alerts if a['alert_level'] == 'high']),
            'generated_at': format_moscow_date(datetime.utcnow())
        })
        
    except Exception as e:
        logger.error(f"Error getting slow response alerts: {e}")
        return jsonify({"error": "Internal server error"}), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500
