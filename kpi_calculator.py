import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from models import Message, Chat, KpiLive
from config_manager import ConfigManager
from response_time_analyzer import ResponseTimeAnalyzer

logger = logging.getLogger(__name__)


class KpiCalculator:
    """Calculate KPI metrics for customer service monitoring"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.response_analyzer = ResponseTimeAnalyzer()
    
    def calculate_chat_kpis(self, session: Session, chat_id: int, start_time: datetime, end_time: datetime) -> Optional[Dict]:
        """
        Calculate comprehensive KPIs for a specific chat in a time period
        
        Args:
            session: Database session
            chat_id: Chat ID to calculate KPIs for
            start_time: Start of the period
            end_time: End of the period
            
        Returns:
            Dictionary with calculated KPIs
        """
        try:
            # Get all messages in the period
            messages = session.query(Message).filter(
                Message.chat_id == chat_id,
                Message.timestamp >= start_time,
                Message.timestamp <= end_time
            ).order_by(Message.timestamp).all()
            
            if not messages:
                return None
            
            # Calculate basic metrics
            total_messages = len(messages)
            client_messages = [m for m in messages if not m.is_team_member]
            team_messages = [m for m in messages if m.is_team_member]
            
            # Calculate response time metrics using improved analyzer
            response_times = self.response_analyzer.analyze_chat_response_times(session, chat_id, start_time, end_time)
            
            # Calculate unanswered messages
            unanswered_count = self._calculate_unanswered_messages(session, chat_id, start_time, end_time)
            
            # Calculate sentiment metrics
            sentiment_metrics = self._calculate_sentiment_metrics(messages)
            
            # Determine if chat needs attention
            attention_info = self._evaluate_attention_needed(
                response_times, unanswered_count, len(client_messages), sentiment_metrics
            )
            
            kpis = {
                # Enhanced response time metrics
                "avg_response_time_seconds": response_times.get("avg_response_time_seconds"),
                "max_response_time_seconds": response_times.get("max_response_time_seconds"),
                "min_response_time_seconds": response_times.get("min_response_time_seconds"),
                "median_response_time_seconds": response_times.get("median_response_time_seconds"),
                "p75_response_time_seconds": response_times.get("p75_response_time_seconds"),
                "p90_response_time_seconds": response_times.get("p90_response_time_seconds"),
                "p95_response_time_seconds": response_times.get("p95_response_time_seconds"),
                
                # Response time in minutes for display
                "avg_response_time_minutes": response_times.get("avg_response_time_minutes"),
                "max_response_time_minutes": response_times.get("max_response_time_minutes"),
                "min_response_time_minutes": response_times.get("min_response_time_minutes"),
                "median_response_time_minutes": response_times.get("median_response_time_minutes"),
                
                # Response distribution metrics
                "total_responses": response_times.get("total_responses", 0),
                "responses_under_5min": response_times.get("responses_under_5min", 0),
                "responses_under_15min": response_times.get("responses_under_15min", 0),
                "responses_under_1hour": response_times.get("responses_under_1hour", 0),
                "responses_over_1hour": response_times.get("responses_over_1hour", 0),
                "percentage_under_5min": response_times.get("percentage_under_5min", 0),
                "percentage_under_15min": response_times.get("percentage_under_15min", 0),
                "percentage_under_1hour": response_times.get("percentage_under_1hour", 0),
                "percentage_over_1hour": response_times.get("percentage_over_1hour", 0),
                
                # Message distribution
                "total_messages": total_messages,
                "client_messages": len(client_messages),
                "team_messages": len(team_messages),
                "unanswered_messages": unanswered_count,
                "unanswered_percentage": (unanswered_count / len(client_messages) * 100) if client_messages else 0,
                
                # Sentiment metrics
                "positive_messages": sentiment_metrics.get("positive", 0),
                "negative_messages": sentiment_metrics.get("negative", 0),
                "neutral_messages": sentiment_metrics.get("neutral", 0),
                "avg_sentiment_score": sentiment_metrics.get("avg_score"),
                
                # Attention flags
                "needs_attention": attention_info["needs_attention"],
                "attention_reasons": attention_info["reasons"]
            }
            
            return kpis
            
        except Exception as e:
            logger.error(f"Error calculating KPIs for chat {chat_id}: {e}")
            return None
    
    def _calculate_response_times(self, session: Session, chat_id: int, start_time: datetime, end_time: datetime) -> Dict:
        """Calculate response time statistics"""
        try:
            # Get messages with response times
            response_times_query = session.query(Message.response_time_seconds).filter(
                Message.chat_id == chat_id,
                Message.timestamp >= start_time,
                Message.timestamp <= end_time,
                Message.response_time_seconds.isnot(None),
                Message.response_time_seconds > 0
            ).all()
            
            response_times = [rt[0] for rt in response_times_query if rt[0]]
            
            if not response_times:
                return {"avg": None, "max": None, "median": None}
            
            # Calculate statistics
            avg_response_time = int(sum(response_times) / len(response_times))
            max_response_time = max(response_times)
            
            # Calculate median
            sorted_times = sorted(response_times)
            n = len(sorted_times)
            if n % 2 == 0:
                median_response_time = int((sorted_times[n//2 - 1] + sorted_times[n//2]) / 2)
            else:
                median_response_time = sorted_times[n//2]
            
            return {
                "avg": avg_response_time,
                "max": max_response_time,
                "median": median_response_time
            }
            
        except Exception as e:
            logger.error(f"Error calculating response times: {e}")
            return {"avg": None, "max": None, "median": None}
    
    def _calculate_unanswered_messages(self, session: Session, chat_id: int, start_time: datetime, end_time: datetime) -> int:
        """Calculate number of unanswered client messages"""
        try:
            # Messages that are older than 60 minutes and still unanswered
            cutoff_time = datetime.utcnow() - timedelta(minutes=60)
            
            unanswered_count = session.query(Message).filter(
                Message.chat_id == chat_id,
                Message.timestamp >= start_time,
                Message.timestamp <= min(end_time, cutoff_time),  # Only count messages older than 60 min
                Message.is_team_member == False,
                Message.is_answered == False
            ).count()
            
            return unanswered_count
            
        except Exception as e:
            logger.error(f"Error calculating unanswered messages: {e}")
            return 0
    
    def _calculate_sentiment_metrics(self, messages: List[Message]) -> Dict:
        """Calculate sentiment distribution and average"""
        try:
            sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
            sentiment_scores = []
            
            for message in messages:
                if message.sentiment_label:
                    sentiment_counts[message.sentiment_label] = sentiment_counts.get(message.sentiment_label, 0) + 1
                
                if message.sentiment_score is not None:
                    sentiment_scores.append(message.sentiment_score)
            
            avg_score = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else None
            
            return {
                "positive": sentiment_counts["positive"],
                "negative": sentiment_counts["negative"],
                "neutral": sentiment_counts["neutral"],
                "avg_score": avg_score
            }
            
        except Exception as e:
            logger.error(f"Error calculating sentiment metrics: {e}")
            return {"positive": 0, "negative": 0, "neutral": 0, "avg_score": None}
    
    def _evaluate_attention_needed(self, response_times: Dict, unanswered_count: int, 
                                   client_message_count: int, sentiment_metrics: Dict) -> Dict:
        """Evaluate if chat needs attention based on KPI thresholds"""
        try:
            thresholds = self.config.get_kpi_thresholds()
            needs_attention = False
            reasons = []
            
            # Check average response time
            if response_times.get("avg") and response_times["avg"] > thresholds.get("max_avg_response_time", 3600):
                needs_attention = True
                reasons.append("High average response time")
            
            # Check maximum response time
            if response_times.get("max") and response_times["max"] > thresholds.get("max_response_time", 7200):
                needs_attention = True
                reasons.append("Very long response time detected")
            
            # Check unanswered percentage
            if client_message_count > 0:
                unanswered_percentage = (unanswered_count / client_message_count) * 100
                if unanswered_percentage > thresholds.get("max_unanswered_percentage", 20):
                    needs_attention = True
                    reasons.append("High percentage of unanswered messages")
            
            # Check negative sentiment
            if sentiment_metrics.get("negative", 0) > thresholds.get("max_negative_messages", 5):
                needs_attention = True
                reasons.append("High number of negative messages")
            
            # Check average sentiment score
            if (sentiment_metrics.get("avg_score") is not None and 
                sentiment_metrics["avg_score"] < thresholds.get("min_avg_sentiment", -0.3)):
                needs_attention = True
                reasons.append("Low average sentiment score")
            
            return {
                "needs_attention": needs_attention,
                "reasons": reasons
            }
            
        except Exception as e:
            logger.error(f"Error evaluating attention needed: {e}")
            return {"needs_attention": False, "reasons": []}
    
    def get_dashboard_summary(self, session: Session, hours: int = 24) -> Dict:
        """Get summary statistics for dashboard"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Get latest KPIs for all chats
            latest_kpis = session.query(KpiLive).filter(
                KpiLive.calculated_at >= start_time
            ).order_by(KpiLive.calculated_at.desc()).all()
            
            if not latest_kpis:
                return {}
            
            # Aggregate statistics
            total_chats = len(set(kpi.chat_id for kpi in latest_kpis))
            chats_needing_attention = len([kpi for kpi in latest_kpis if kpi.needs_attention])
            
            all_response_times = [kpi.avg_response_time_seconds for kpi in latest_kpis 
                                if kpi.avg_response_time_seconds is not None]
            
            total_messages = sum(kpi.total_messages for kpi in latest_kpis)
            total_client_messages = sum(kpi.client_messages for kpi in latest_kpis)
            total_team_messages = sum(kpi.team_messages for kpi in latest_kpis)
            
            return {
                "total_chats": total_chats,
                "chats_needing_attention": chats_needing_attention,
                "avg_response_time": int(sum(all_response_times) / len(all_response_times)) if all_response_times else None,
                "total_messages": total_messages,
                "client_messages": total_client_messages,
                "team_messages": total_team_messages,
                "activity_distribution": {
                    "client_percentage": (total_client_messages / total_messages * 100) if total_messages else 0,
                    "team_percentage": (total_team_messages / total_messages * 100) if total_messages else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard summary: {e}")
            return {}
