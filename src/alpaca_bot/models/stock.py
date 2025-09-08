"""Stock data models for the Alpaca trading bot.

This module defines data classes and models for representing stock information,
market data, and technical analysis indicators.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class StockQuote:
    """Represents a real-time stock quote."""
    
    symbol: str
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    timestamp: datetime
    
    def __post_init__(self) -> None:
        """Post-initialization validation."""
        if self.bid <= 0 or self.ask <= 0:
            raise ValueError("Bid and ask prices must be positive")
        if self.bid > self.ask:
            raise ValueError("Bid price cannot be higher than ask price")
    
    @property
    def spread(self) -> float:
        """Calculate bid-ask spread."""
        if self.ask is None or self.bid is None:
            return 0.0
        return self.ask - self.bid
    
    @property
    def spread_percent(self) -> float:
        """Calculate bid-ask spread as percentage of mid price."""
        if self.ask is None or self.bid is None:
            return 0.0
        mid_price = (self.bid + self.ask) / 2
        if mid_price == 0:
            return 0.0
        return (self.spread / mid_price) * 100
    
    @property
    def mid_price(self) -> float:
        """Calculate mid price between bid and ask."""
        if self.ask is None or self.bid is None:
            return 0.0
        return (self.bid + self.ask) / 2
    
    def to_dict(self) -> dict:
        """Convert quote to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'bid': self.bid,
            'ask': self.ask,
            'bid_size': self.bid_size,
            'ask_size': self.ask_size,
            'timestamp': self.timestamp.isoformat(),
            'spread': self.spread,
            'spread_percent': self.spread_percent,
            'mid_price': self.mid_price,
        }


@dataclass
class StockBar:
    """Represents a single price bar (OHLCV data)."""
    
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    def __post_init__(self) -> None:
        """Post-initialization validation."""
        if any(price <= 0 for price in [self.open, self.high, self.low, self.close]):
            raise ValueError("All prices must be positive")
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")
        if not (self.low <= self.open <= self.high and self.low <= self.close <= self.high):
            raise ValueError("Invalid OHLC relationship")
    
    @property
    def body_size(self) -> float:
        """Calculate the size of the candle body."""
        return abs(self.close - self.open)
    
    @property
    def upper_shadow(self) -> float:
        """Calculate the upper shadow length."""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_shadow(self) -> float:
        """Calculate the lower shadow length."""
        return min(self.open, self.close) - self.low
    
    @property
    def is_bullish(self) -> bool:
        """Check if the bar is bullish (close > open)."""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """Check if the bar is bearish (close < open)."""
        return self.close < self.open
    
    @property
    def is_doji(self) -> bool:
        """Check if the bar is a doji (open ≈ close)."""
        return abs(self.close - self.open) < 0.01  # Threshold for doji
    
    def to_dict(self) -> dict:
        """Convert bar to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'body_size': self.body_size,
            'upper_shadow': self.upper_shadow,
            'lower_shadow': self.lower_shadow,
            'is_bullish': self.is_bullish,
            'is_bearish': self.is_bearish,
            'is_doji': self.is_doji,
        }


@dataclass
class SupportResistanceLevel:
    """Represents a support or resistance level."""
    
    price: float
    level_type: str  # 'support' or 'resistance'
    strength: float  # 0.0 to 1.0, higher means stronger
    touches: int  # Number of times price touched this level
    last_touch: datetime
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self) -> None:
        """Post-initialization validation."""
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.level_type not in ['support', 'resistance']:
            raise ValueError("Level type must be 'support' or 'resistance'")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("Strength must be between 0.0 and 1.0")
        if self.touches < 0:
            raise ValueError("Touches cannot be negative")
    
    @property
    def is_support(self) -> bool:
        """Check if this is a support level."""
        return self.level_type == 'support'
    
    @property
    def is_resistance(self) -> bool:
        """Check if this is a resistance level."""
        return self.level_type == 'resistance'
    
    @property
    def age_hours(self) -> float:
        """Calculate age of the level in hours."""
        return (datetime.now() - self.created_at).total_seconds() / 3600
    
    def update_touch(self, timestamp: datetime) -> None:
        """Update the level when price touches it."""
        self.touches += 1
        self.last_touch = timestamp
        # Increase strength with more touches (with diminishing returns)
        self.strength = min(1.0, self.strength + 0.1 * (1 - self.strength))
    
    def to_dict(self) -> dict:
        """Convert level to dictionary for serialization."""
        return {
            'price': self.price,
            'level_type': self.level_type,
            'strength': self.strength,
            'touches': self.touches,
            'last_touch': self.last_touch.isoformat(),
            'created_at': self.created_at.isoformat(),
            'age_hours': self.age_hours,
            'is_support': self.is_support,
            'is_resistance': self.is_resistance,
        }


@dataclass
class TechnicalIndicators:
    """Container for technical analysis indicators."""
    
    symbol: str
    timestamp: datetime
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    bollinger_middle: Optional[float] = None
    volume_sma: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert indicators to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'sma_20': self.sma_20,
            'sma_50': self.sma_50,
            'ema_12': self.ema_12,
            'ema_26': self.ema_26,
            'rsi': self.rsi,
            'macd': self.macd,
            'macd_signal': self.macd_signal,
            'macd_histogram': self.macd_histogram,
            'bollinger_upper': self.bollinger_upper,
            'bollinger_lower': self.bollinger_lower,
            'bollinger_middle': self.bollinger_middle,
            'volume_sma': self.volume_sma,
        }


@dataclass
class StockData:
    """Comprehensive stock data container."""
    
    symbol: str
    company_name: str
    current_quote: Optional[StockQuote] = None
    latest_bar: Optional[StockBar] = None
    historical_bars: List[StockBar] = field(default_factory=list)
    support_levels: List[SupportResistanceLevel] = field(default_factory=list)
    resistance_levels: List[SupportResistanceLevel] = field(default_factory=list)
    technical_indicators: Optional[TechnicalIndicators] = None
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def current_price(self) -> Optional[float]:
        """Get current price from quote or latest bar."""
        if self.current_quote:
            return self.current_quote.mid_price
        elif self.latest_bar:
            return self.latest_bar.close
        return None
    
    @property
    def strongest_support(self) -> Optional[SupportResistanceLevel]:
        """Get the strongest support level."""
        if not self.support_levels:
            return None
        return max(self.support_levels, key=lambda x: x.strength)
    
    @property
    def strongest_resistance(self) -> Optional[SupportResistanceLevel]:
        """Get the strongest resistance level."""
        if not self.resistance_levels:
            return None
        return max(self.resistance_levels, key=lambda x: x.strength)
    
    @property
    def nearest_support(self) -> Optional[SupportResistanceLevel]:
        """Get the nearest support level below current price."""
        current = self.current_price
        if not current or not self.support_levels:
            return None
        
        below_current = [level for level in self.support_levels if level.price < current]
        if not below_current:
            return None
        
        return max(below_current, key=lambda x: x.price)
    
    @property
    def nearest_resistance(self) -> Optional[SupportResistanceLevel]:
        """Get the nearest resistance level above current price."""
        current = self.current_price
        if not current or not self.resistance_levels:
            return None
        
        above_current = [level for level in self.resistance_levels if level.price > current]
        if not above_current:
            return None
        
        return min(above_current, key=lambda x: x.price)
    
    def add_bar(self, bar: StockBar) -> None:
        """Add a new price bar to historical data."""
        self.historical_bars.append(bar)
        self.latest_bar = bar
        self.last_updated = datetime.now()
        
        # Keep only last 1000 bars to manage memory
        if len(self.historical_bars) > 1000:
            self.historical_bars = self.historical_bars[-1000:]
    
    def update_quote(self, quote: StockQuote) -> None:
        """Update current quote."""
        self.current_quote = quote
        self.last_updated = datetime.now()
    
    def add_support_level(self, level: SupportResistanceLevel) -> None:
        """Add a support level."""
        if level.is_support:
            self.support_levels.append(level)
    
    def add_resistance_level(self, level: SupportResistanceLevel) -> None:
        """Add a resistance level."""
        if level.is_resistance:
            self.resistance_levels.append(level)
    
    def get_bars_dataframe(self) -> pd.DataFrame:
        """Convert historical bars to pandas DataFrame."""
        if not self.historical_bars:
            return pd.DataFrame()
        
        data = []
        for bar in self.historical_bars:
            data.append({
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume,
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    def to_dict(self) -> dict:
        """Convert stock data to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'company_name': self.company_name,
            'current_quote': self.current_quote.to_dict() if self.current_quote else None,
            'latest_bar': self.latest_bar.to_dict() if self.latest_bar else None,
            'support_levels': [level.to_dict() for level in self.support_levels],
            'resistance_levels': [level.to_dict() for level in self.resistance_levels],
            'technical_indicators': self.technical_indicators.to_dict() if self.technical_indicators else None,
            'last_updated': self.last_updated.isoformat(),
            'current_price': self.current_price,
        }