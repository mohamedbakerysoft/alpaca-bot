"""Market utilities for the Alpaca trading bot.

This module provides utilities for:
- Market hours detection
- Trading session validation
- Market status checking
"""

import logging
from datetime import datetime, time
from typing import Tuple, Optional
import pytz
from ..config.settings import settings


class MarketHours:
    """Market hours utility class."""
    
    def __init__(self):
        """Initialize market hours utility."""
        self.logger = logging.getLogger(__name__)
        self.eastern_tz = pytz.timezone('US/Eastern')
        
    def is_market_open(self) -> bool:
        """Check if the market is currently open.
        
        Returns:
            bool: True if market is open, False otherwise.
        """
        now_et = datetime.now(self.eastern_tz)
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        if now_et.weekday() >= 5:  # Saturday or Sunday
            return False
            
        # Get current time
        current_time = now_et.time()
        
        # Get trading hours from settings
        start_hour = getattr(settings, 'trading_start_hour', 9)
        start_minute = getattr(settings, 'trading_start_minute', 30)
        end_hour = getattr(settings, 'trading_end_hour', 16)
        end_minute = getattr(settings, 'trading_end_minute', 0)
        
        # Create time objects for market open/close
        market_open = time(start_hour, start_minute)
        market_close = time(end_hour, end_minute)
        
        # Check if current time is within trading hours
        return market_open <= current_time <= market_close
    
    def get_market_status(self) -> Tuple[bool, str]:
        """Get detailed market status.
        
        Returns:
            Tuple[bool, str]: (is_open, status_message)
        """
        now_et = datetime.now(self.eastern_tz)
        
        # Check if it's a weekday
        if now_et.weekday() >= 5:  # Weekend
            next_monday = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
            days_until_monday = (7 - now_et.weekday()) % 7
            if days_until_monday == 0:  # It's Sunday
                days_until_monday = 1
            next_monday = next_monday.replace(day=now_et.day + days_until_monday)
            return False, f"Market closed (Weekend). Opens Monday at 9:30 AM ET"
        
        # Get trading hours from settings
        start_hour = getattr(settings, 'trading_start_hour', 9)
        start_minute = getattr(settings, 'trading_start_minute', 30)
        end_hour = getattr(settings, 'trading_end_hour', 16)
        end_minute = getattr(settings, 'trading_end_minute', 0)
        
        current_time = now_et.time()
        market_open = time(start_hour, start_minute)
        market_close = time(end_hour, end_minute)
        
        if current_time < market_open:
            return False, f"Market closed. Opens at {start_hour:02d}:{start_minute:02d} ET"
        elif current_time > market_close:
            tomorrow = now_et.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
            tomorrow = tomorrow.replace(day=now_et.day + 1)
            return False, f"Market closed. Opens tomorrow at {start_hour:02d}:{start_minute:02d} ET"
        else:
            return True, f"Market open until {end_hour:02d}:{end_minute:02d} ET"
    
    def get_time_until_open(self) -> Optional[str]:
        """Get time until market opens.
        
        Returns:
            Optional[str]: Time until market opens, or None if market is open.
        """
        is_open, _ = self.get_market_status()
        if is_open:
            return None
            
        now_et = datetime.now(self.eastern_tz)
        
        # Get trading hours from settings
        start_hour = getattr(settings, 'trading_start_hour', 9)
        start_minute = getattr(settings, 'trading_start_minute', 30)
        
        # Calculate next market open
        next_open = now_et.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        
        # If market opening time has passed today, move to next business day
        if now_et.time() > time(start_hour, start_minute) or now_et.weekday() >= 5:
            # Move to next business day
            days_to_add = 1
            if now_et.weekday() == 4:  # Friday
                days_to_add = 3  # Skip to Monday
            elif now_et.weekday() == 5:  # Saturday
                days_to_add = 2  # Skip to Monday
            
            next_open = next_open.replace(day=now_et.day + days_to_add)
        
        time_diff = next_open - now_et
        hours, remainder = divmod(time_diff.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        
        if hours >= 24:
            days = int(hours // 24)
            hours = int(hours % 24)
            return f"{days}d {hours}h {int(minutes)}m"
        else:
            return f"{int(hours)}h {int(minutes)}m"
    
    def get_current_et_time(self) -> str:
        """Get current Eastern Time as formatted string.
        
        Returns:
            str: Current time in ET timezone.
        """
        now_et = datetime.now(self.eastern_tz)
        return now_et.strftime("%Y-%m-%d %H:%M:%S %Z")


# Global market hours instance
market_hours = MarketHours()