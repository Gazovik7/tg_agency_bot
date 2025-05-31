"""
Timezone utilities for handling Moscow time conversion
"""
import pytz
from datetime import datetime
from config_manager import ConfigManager

def get_moscow_timezone():
    """Get Moscow timezone object"""
    return pytz.timezone('Europe/Moscow')

def get_configured_timezone():
    """Get timezone from configuration"""
    config = ConfigManager()
    timezone_name = config.get_config().get('agency', {}).get('timezone', 'UTC')
    return pytz.timezone(timezone_name)

def utc_to_moscow(utc_dt):
    """Convert UTC datetime to Moscow time"""
    if utc_dt is None:
        return None
    
    try:
        # If datetime is naive, assume it's UTC
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        
        moscow_tz = get_moscow_timezone()
        return utc_dt.astimezone(moscow_tz)
    except Exception:
        return None

def utc_to_configured_timezone(utc_dt):
    """Convert UTC datetime to configured timezone"""
    if utc_dt is None:
        return None
    
    try:
        # If datetime is naive, assume it's UTC
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        
        configured_tz = get_configured_timezone()
        return utc_dt.astimezone(configured_tz)
    except Exception:
        return None

def now_in_moscow():
    """Get current time in Moscow timezone"""
    moscow_tz = get_moscow_timezone()
    return datetime.now(moscow_tz)

def now_in_configured_timezone():
    """Get current time in configured timezone"""
    configured_tz = get_configured_timezone()
    return datetime.now(configured_tz)

def format_moscow_time(dt, format_str='%Y-%m-%d %H:%M:%S'):
    """Format datetime in Moscow timezone"""
    if dt is None:
        return None
    
    moscow_dt = utc_to_moscow(dt)
    if moscow_dt is None:
        return None
    return moscow_dt.strftime(format_str)

def format_configured_time(dt, format_str='%Y-%m-%d %H:%M:%S'):
    """Format datetime in configured timezone"""
    if dt is None:
        return None
    
    configured_dt = utc_to_configured_timezone(dt)
    if configured_dt is None:
        return None
    return configured_dt.strftime(format_str)