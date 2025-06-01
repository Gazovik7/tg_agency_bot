"""
Utilities for timezone handling
"""
import pytz
from datetime import datetime, timedelta

# Moscow timezone
MOSCOW_TZ = pytz.timezone('Europe/Moscow')
UTC_TZ = pytz.utc

def utc_to_moscow(utc_dt):
    """Convert UTC datetime to Moscow timezone"""
    if utc_dt is None:
        return None
    
    if utc_dt.tzinfo is None:
        utc_dt = UTC_TZ.localize(utc_dt)
    
    return utc_dt.astimezone(MOSCOW_TZ)

def moscow_to_utc(moscow_dt):
    """Convert Moscow timezone datetime to UTC"""
    if moscow_dt is None:
        return None
    
    if moscow_dt.tzinfo is None:
        moscow_dt = MOSCOW_TZ.localize(moscow_dt)
    
    return moscow_dt.astimezone(UTC_TZ)

def moscow_date_to_utc_range(date_str):
    """Convert Moscow date string to UTC datetime range for the full day"""
    moscow_date = datetime.strptime(date_str, '%Y-%m-%d')
    
    # Start of day in Moscow
    moscow_start = MOSCOW_TZ.localize(moscow_date.replace(hour=0, minute=0, second=0, microsecond=0))
    # End of day in Moscow
    moscow_end = MOSCOW_TZ.localize(moscow_date.replace(hour=23, minute=59, second=59, microsecond=999999))
    
    # Convert to UTC
    utc_start = moscow_start.astimezone(UTC_TZ)
    utc_end = moscow_end.astimezone(UTC_TZ)
    
    return utc_start, utc_end

def get_moscow_now():
    """Get current datetime in Moscow timezone"""
    return datetime.now(MOSCOW_TZ)

def format_moscow_datetime(utc_dt, format_str='%d.%m.%Y %H:%M'):
    """Format UTC datetime as Moscow timezone string"""
    if utc_dt is None:
        return None
    
    moscow_dt = utc_to_moscow(utc_dt)
    return moscow_dt.strftime(format_str)

def format_moscow_date(utc_dt):
    """Format UTC datetime as Moscow date string"""
    return format_moscow_datetime(utc_dt, '%Y-%m-%d')

def format_configured_time(utc_dt):
    """Format UTC datetime as Moscow timezone string (alias for format_moscow_datetime)"""
    return format_moscow_datetime(utc_dt)