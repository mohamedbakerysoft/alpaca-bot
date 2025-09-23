"""Market utilities for the Alpaca trading bot.

This module provides utilities for:
- Market hours detection
- Trading session validation
- Market status checking
"""

import logging
from datetime import datetime, time, timedelta
from typing import Tuple, Optional
import pytz
from ..config.settings import settings


class MarketHours:
    """Market hours utility class."""
    
    @staticmethod
    def is_market_open(weekend_trading_enabled: bool = False, extended_hours_enabled: bool = False) -> bool:
        """Check if the market is currently open.
        
        Args:
            weekend_trading_enabled (bool): Whether weekend trading is enabled.
            extended_hours_enabled (bool): Whether extended hours trading is enabled.
        
        Returns:
            bool: True if market is open, False otherwise.
        """
        eastern_tz = pytz.timezone('US/Eastern')
        now_et = datetime.now(eastern_tz)
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        if now_et.weekday() >= 5 and not weekend_trading_enabled:  # Saturday or Sunday
            return False
            
        # Get current time
        current_time = now_et.time()
        
        # Determine trading hours based on extended hours setting
        if extended_hours_enabled and now_et.weekday() < 5:  # Extended hours only on weekdays
            start_hour = getattr(settings, 'extended_hours_start_hour', 4)
            start_minute = getattr(settings, 'extended_hours_start_minute', 0)
            end_hour = getattr(settings, 'extended_hours_end_hour', 20)
            end_minute = getattr(settings, 'extended_hours_end_minute', 0)
        else:
            # Regular trading hours
            start_hour = getattr(settings, 'trading_start_hour', 9)
            start_minute = getattr(settings, 'trading_start_minute', 30)
            end_hour = getattr(settings, 'trading_end_hour', 16)
            end_minute = getattr(settings, 'trading_end_minute', 0)
        
        # Create time objects for market open/close
        market_open = time(start_hour, start_minute)
        market_close = time(end_hour, end_minute)
        
        # For weekend trading, allow 24/7 trading on weekends
        if weekend_trading_enabled and now_et.weekday() >= 5:
            return True
        
        # Check if current time is within trading hours
        return market_open <= current_time <= market_close
    
    @staticmethod
    def get_market_status(weekend_trading_enabled: bool = False, extended_hours_enabled: bool = False) -> str:
        """Get current market status message.
        
        Args:
            weekend_trading_enabled (bool): Whether weekend trading is enabled.
            extended_hours_enabled (bool): Whether extended hours trading is enabled.
        
        Returns:
            str: Market status message.
        """
        eastern_tz = pytz.timezone('US/Eastern')
        now_et = datetime.now(eastern_tz)
        current_time = now_et.time()
        current_weekday = now_et.weekday()
        
        # Check if it's weekend
        if current_weekday >= 5:
            if weekend_trading_enabled:
                return "Weekend trading is enabled - Market is open"
            else:
                return "Market is closed (Weekend). Opens Monday at 9:30 AM ET."
        
        # Check if market is open
        if MarketHours.is_market_open(weekend_trading_enabled, extended_hours_enabled):
            if extended_hours_enabled:
                # Determine which session we're in
                regular_open = time(9, 30)
                regular_close = time(16, 0)
                
                if current_time < regular_open:
                    return "Market is open (Pre-market extended hours)"
                elif current_time <= regular_close:
                    return "Market is open (Regular hours)"
                else:
                    return "Market is open (After-hours extended hours)"
            else:
                return "Market is open (Regular hours)"
        
        # Market is closed during weekday
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        
        if now_et < market_open:
            return f"Market opens at 9:30 AM ET (in {MarketHours.get_time_until_open()})"
        else:
            return "Market is closed. Opens tomorrow at 9:30 AM ET."
    
    @staticmethod
    def get_time_until_open() -> Optional[str]:
        """Get time until market opens.
        
        Returns:
            Optional[str]: Time until market opens, or None if market is open.
        """
        is_open = MarketHours.is_market_open()
        if is_open:
            return None
            
        eastern_tz = pytz.timezone('US/Eastern')
        now_et = datetime.now(eastern_tz)
        
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
            
            next_open = next_open + timedelta(days=days_to_add)
        
        time_diff = next_open - now_et
        hours, remainder = divmod(time_diff.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        
        if hours >= 24:
            days = int(hours // 24)
            hours = int(hours % 24)
            return f"{days}d {hours}h {int(minutes)}m"
        else:
            return f"{int(hours)}h {int(minutes)}m"
    
    @staticmethod
    def get_current_et_time() -> datetime:
        """Get current Eastern Time as datetime object.
        
        Returns:
            datetime: Current time in ET timezone.
        """
        eastern_tz = pytz.timezone('US/Eastern')
        return datetime.now(eastern_tz)
    
    @staticmethod
    def get_trading_session_type() -> str:
        """Get the current trading session type.
        
        Returns:
            str: Trading session type ('pre_market', 'regular', 'after_hours', 'closed')
        """
        eastern_tz = pytz.timezone('US/Eastern')
        now_et = datetime.now(eastern_tz)
        current_time = now_et.time()
        current_weekday = now_et.weekday()
        
        # Check if it's weekend
        if current_weekday >= 5:
            return 'closed'
        
        # Define session times
        pre_market_start = time(4, 0)   # 4:00 AM ET
        regular_start = time(9, 30)     # 9:30 AM ET
        regular_end = time(16, 0)       # 4:00 PM ET
        after_hours_end = time(20, 0)   # 8:00 PM ET
        
        if pre_market_start <= current_time < regular_start:
            return 'pre_market'
        elif regular_start <= current_time <= regular_end:
            return 'regular'
        elif regular_end < current_time <= after_hours_end:
            return 'after_hours'
        else:
            return 'closed'
    
    @staticmethod
    def is_extended_hours_session() -> bool:
        """Check if current time is in extended hours (pre-market or after-hours).
        
        Returns:
            bool: True if in extended hours, False otherwise.
        """
        session_type = MarketHours.get_trading_session_type()
        return session_type in ['pre_market', 'after_hours']
    
    @staticmethod
    def is_extended_hours() -> bool:
        """Check if current time is in extended hours and extended hours is enabled.
        
        Returns:
            bool: True if in extended hours and enabled, False otherwise.
        """
        if not getattr(settings, 'extended_hours_enabled', False):
            return False
        
        return MarketHours.is_extended_hours_session()
    
    @staticmethod
    def should_stop_weekend_trading() -> bool:
        """Check if trading should be stopped for the weekend.
        
        Returns:
            bool: True if trading should be stopped, False otherwise.
        """
        eastern_tz = pytz.timezone('US/Eastern')
        now_et = datetime.now(eastern_tz)
        current_weekday = now_et.weekday()
        current_time = now_et.time()
        
        # Stop trading on Friday after market close if weekend trading is disabled
        weekend_trading_enabled = getattr(settings, 'weekend_trading_enabled', False)
        if not weekend_trading_enabled:
            if current_weekday == 4:  # Friday
                market_close = time(20, 0)  # 8:00 PM ET (end of extended hours)
                if current_time >= market_close:
                    return True
            elif current_weekday >= 5:  # Weekend
                return True
        
        return False
    
    @staticmethod
    def get_next_trading_session() -> datetime:
        """Get the next trading session start time.
        
        Returns:
            datetime: Next trading session start time in ET.
        """
        eastern_tz = pytz.timezone('US/Eastern')
        now_et = datetime.now(eastern_tz)
        current_weekday = now_et.weekday()
        
        # Determine next trading day
        if current_weekday == 4:  # Friday
            # Next trading is Monday
            days_to_add = 3
        elif current_weekday == 5:  # Saturday
            # Next trading is Monday
            days_to_add = 2
        elif current_weekday == 6:  # Sunday
            # Next trading is Monday
            days_to_add = 1
        else:
            # Next trading day
            days_to_add = 1
        
        next_trading_day = now_et + timedelta(days=days_to_add)
        
        # Set to market open time
        if getattr(settings, 'extended_hours_enabled', False):
            start_hour = getattr(settings, 'extended_hours_start_hour', 4)
            start_minute = getattr(settings, 'extended_hours_start_minute', 0)
        else:
            start_hour = getattr(settings, 'trading_start_hour', 9)
            start_minute = getattr(settings, 'trading_start_minute', 30)
        
        return next_trading_day.replace(
            hour=start_hour, 
            minute=start_minute, 
            second=0, 
            microsecond=0
        )


# Global market hours instance
market_hours = MarketHours()