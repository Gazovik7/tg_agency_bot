"""
Модуль для автоматического связывания сотрудников по username
"""
import logging
from sqlalchemy.orm import Session
from models import TeamMember, Message
from app import db

logger = logging.getLogger(__name__)

class TeamMemberLinker:
    """Класс для автоматического связывания сотрудников с их Telegram ID"""
    
    def __init__(self):
        pass
    
    def check_and_link_member(self, user_id: int, username: str, full_name: str) -> bool:
        """
        Проверяет, есть ли несвязанный сотрудник с таким username и связывает его
        
        Args:
            user_id: Telegram ID пользователя
            username: Username пользователя (без @)
            full_name: Полное имя пользователя
            
        Returns:
            True если сотрудник был найден и связан, False иначе
        """
        try:
            if not username:
                return False
            
            # Ищем несвязанного сотрудника с таким username
            team_member = TeamMember.query.filter_by(
                username=username,
                is_linked=False
            ).first()
            
            if team_member:
                # Проверяем, что user_id еще не занят другим сотрудником
                existing_member = TeamMember.query.filter_by(user_id=user_id).first()
                if existing_member:
                    logger.warning(f"User ID {user_id} уже связан с другим сотрудником: {existing_member.full_name}")
                    return False
                
                # Связываем сотрудника
                team_member.user_id = user_id
                team_member.is_linked = True
                
                # Обновляем полное имя, если оно изменилось
                if full_name and full_name != team_member.full_name:
                    logger.info(f"Обновляем имя сотрудника {team_member.full_name} -> {full_name}")
                    team_member.full_name = full_name
                
                db.session.commit()
                
                # Обновляем все существующие сообщения этого пользователя
                updated_messages = Message.query.filter_by(user_id=user_id).update(
                    {'is_team_member': team_member.is_active}
                )
                db.session.commit()
                
                logger.info(f"Сотрудник {team_member.full_name} (@{username}) успешно связан с ID {user_id}. "
                          f"Обновлено {updated_messages} сообщений.")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при связывании сотрудника: {e}")
            db.session.rollback()
            return False
    
    def is_team_member(self, user_id: int, username: str = None) -> bool:
        """
        Проверяет, является ли пользователь членом команды
        
        Args:
            user_id: Telegram ID пользователя
            username: Username пользователя (необязательно)
            
        Returns:
            True если пользователь является членом команды
        """
        try:
            # Сначала проверяем по user_id
            team_member = TeamMember.query.filter_by(
                user_id=user_id,
                is_active=True
            ).first()
            
            if team_member:
                return True
            
            # Если не найден по user_id и есть username, пытаемся найти по username
            if username:
                team_member = TeamMember.query.filter_by(
                    username=username,
                    is_active=True
                ).first()
                
                if team_member:
                    # Если нашли несвязанного сотрудника, пытаемся его связать
                    if not team_member.is_linked:
                        logger.info(f"Найден несвязанный сотрудник @{username}, пытаемся связать с ID {user_id}")
                        # Здесь мы не связываем автоматически, так как нужно полное имя
                        # Связывание происходит в check_and_link_member
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при проверке членства в команде: {e}")
            return False
    
    def get_unlinked_members(self) -> list:
        """
        Возвращает список несвязанных сотрудников
        
        Returns:
            Список несвязанных сотрудников
        """
        try:
            unlinked_members = TeamMember.query.filter_by(
                is_linked=False,
                is_active=True
            ).all()
            
            return [{
                'id': member.id,
                'username': member.username,
                'full_name': member.full_name,
                'role': member.role,
                'created_at': member.created_at
            } for member in unlinked_members]
            
        except Exception as e:
            logger.error(f"Ошибка при получении несвязанных сотрудников: {e}")
            return []
    
    def get_linking_statistics(self) -> dict:
        """
        Возвращает статистику связывания сотрудников
        
        Returns:
            Словарь со статистикой
        """
        try:
            total_members = TeamMember.query.filter_by(is_active=True).count()
            linked_members = TeamMember.query.filter_by(is_active=True, is_linked=True).count()
            unlinked_members = total_members - linked_members
            
            return {
                'total_members': total_members,
                'linked_members': linked_members,
                'unlinked_members': unlinked_members,
                'linking_percentage': (linked_members / total_members * 100) if total_members > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики связывания: {e}")
            return {
                'total_members': 0,
                'linked_members': 0,
                'unlinked_members': 0,
                'linking_percentage': 0
            }

# Глобальный экземпляр линкера
team_linker = TeamMemberLinker()