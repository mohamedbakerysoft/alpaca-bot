"""Technical analysis utilities for the Alpaca trading bot.

This module provides functions for calculating technical indicators,
identifying support/resistance levels, and analyzing market data.
"""

import logging
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from ..models.stock import SupportResistanceLevel, TechnicalIndicators


logger = logging.getLogger(__name__)


def calculate_sma(data: pd.Series, window: int) -> pd.Series:
    """Calculate Simple Moving Average.
    
    Args:
        data: Price data series.
        window: Number of periods for the moving average.
        
    Returns:
        pd.Series: Simple moving average values.
    """
    return data.rolling(window=window, min_periods=window).mean()


def calculate_ema(data: pd.Series, window: int) -> pd.Series:
    """Calculate Exponential Moving Average.
    
    Args:
        data: Price data series.
        window: Number of periods for the moving average.
        
    Returns:
        pd.Series: Exponential moving average values.
    """
    return data.ewm(span=window, adjust=False).mean()


def calculate_rsi(data: pd.Series, window: int = 14) -> pd.Series:
    """Calculate Relative Strength Index.
    
    Args:
        data: Price data series.
        window: Number of periods for RSI calculation.
        
    Returns:
        pd.Series: RSI values.
    """
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_macd(
    data: pd.Series, 
    fast_period: int = 12, 
    slow_period: int = 26, 
    signal_period: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        data: Price data series.
        fast_period: Fast EMA period.
        slow_period: Slow EMA period.
        signal_period: Signal line EMA period.
        
    Returns:
        Tuple[pd.Series, pd.Series, pd.Series]: MACD line, signal line, histogram.
    """
    ema_fast = calculate_ema(data, fast_period)
    ema_slow = calculate_ema(data, slow_period)
    
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal_period)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    data: pd.Series, 
    window: int = 20, 
    num_std: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands.
    
    Args:
        data: Price data series.
        window: Number of periods for moving average.
        num_std: Number of standard deviations for bands.
        
    Returns:
        Tuple[pd.Series, pd.Series, pd.Series]: Upper band, middle band, lower band.
    """
    middle_band = calculate_sma(data, window)
    std_dev = data.rolling(window=window).std()
    
    upper_band = middle_band + (std_dev * num_std)
    lower_band = middle_band - (std_dev * num_std)
    
    return upper_band, middle_band, lower_band


def calculate_all_indicators(df: pd.DataFrame, symbol: str) -> List[TechnicalIndicators]:
    """Calculate all technical indicators for a DataFrame.
    
    Args:
        df: DataFrame with OHLCV data.
        symbol: Stock symbol.
        
    Returns:
        List[TechnicalIndicators]: List of technical indicators for each timestamp.
    """
    if df.empty or 'close' not in df.columns:
        return []
    
    try:
        # Calculate indicators
        df['sma_20'] = calculate_sma(df['close'], 20)
        df['sma_50'] = calculate_sma(df['close'], 50)
        df['ema_12'] = calculate_ema(df['close'], 12)
        df['ema_26'] = calculate_ema(df['close'], 26)
        df['rsi'] = calculate_rsi(df['close'])
        
        macd, macd_signal, macd_hist = calculate_macd(df['close'])
        df['macd'] = macd
        df['macd_signal'] = macd_signal
        df['macd_histogram'] = macd_hist
        
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(df['close'])
        df['bollinger_upper'] = bb_upper
        df['bollinger_middle'] = bb_middle
        df['bollinger_lower'] = bb_lower
        
        if 'volume' in df.columns:
            df['volume_sma'] = calculate_sma(df['volume'], 20)
        
        # Create TechnicalIndicators objects
        indicators = []
        for timestamp, row in df.iterrows():
            indicator = TechnicalIndicators(
                symbol=symbol,
                timestamp=timestamp,
                sma_20=row.get('sma_20'),
                sma_50=row.get('sma_50'),
                ema_12=row.get('ema_12'),
                ema_26=row.get('ema_26'),
                rsi=row.get('rsi'),
                macd=row.get('macd'),
                macd_signal=row.get('macd_signal'),
                macd_histogram=row.get('macd_histogram'),
                bollinger_upper=row.get('bollinger_upper'),
                bollinger_lower=row.get('bollinger_lower'),
                bollinger_middle=row.get('bollinger_middle'),
                volume_sma=row.get('volume_sma'),
            )
            indicators.append(indicator)
        
        return indicators
        
    except Exception as e:
        logger.error(f"Error calculating indicators for {symbol}: {e}")
        return []


def identify_support_resistance_levels(
    df: pd.DataFrame, 
    window: int = 20, 
    min_touches: int = 2,
    tolerance_percent: float = 0.5
) -> Tuple[List[SupportResistanceLevel], List[SupportResistanceLevel]]:
    """Identify support and resistance levels from price data.
    
    Args:
        df: DataFrame with OHLCV data.
        window: Window size for local extrema detection.
        min_touches: Minimum number of touches to confirm a level.
        tolerance_percent: Price tolerance as percentage for level grouping.
        
    Returns:
        Tuple[List[SupportResistanceLevel], List[SupportResistanceLevel]]: 
        Support levels and resistance levels.
    """
    if df.empty or len(df) < window * 2:
        return [], []
    
    try:
        # Find local minima (potential support) and maxima (potential resistance)
        highs = df['high'].values
        lows = df['low'].values
        timestamps = df.index.tolist()
        
        # Find local extrema
        support_candidates = []
        resistance_candidates = []
        
        for i in range(window, len(df) - window):
            # Check for local minimum (support)
            if lows[i] == min(lows[i-window:i+window+1]):
                support_candidates.append((lows[i], timestamps[i]))
            
            # Check for local maximum (resistance)
            if highs[i] == max(highs[i-window:i+window+1]):
                resistance_candidates.append((highs[i], timestamps[i]))
        
        # Group similar price levels
        support_levels = _group_price_levels(
            support_candidates, tolerance_percent, 'support', min_touches
        )
        resistance_levels = _group_price_levels(
            resistance_candidates, tolerance_percent, 'resistance', min_touches
        )
        
        return support_levels, resistance_levels
        
    except Exception as e:
        logger.error(f"Error identifying support/resistance levels: {e}")
        return [], []


def _group_price_levels(
    candidates: List[Tuple[float, datetime]], 
    tolerance_percent: float, 
    level_type: str,
    min_touches: int
) -> List[SupportResistanceLevel]:
    """Group similar price levels together.
    
    Args:
        candidates: List of (price, timestamp) tuples.
        tolerance_percent: Price tolerance as percentage.
        level_type: 'support' or 'resistance'.
        min_touches: Minimum touches to confirm level.
        
    Returns:
        List[SupportResistanceLevel]: Grouped and filtered levels.
    """
    if not candidates:
        return []
    
    # Sort by price
    candidates.sort(key=lambda x: x[0])
    
    grouped_levels = []
    current_group = [candidates[0]]
    
    for i in range(1, len(candidates)):
        price, timestamp = candidates[i]
        group_avg_price = sum(p for p, _ in current_group) / len(current_group)
        
        # Check if price is within tolerance of current group
        tolerance = group_avg_price * (tolerance_percent / 100)
        
        if abs(price - group_avg_price) <= tolerance:
            current_group.append((price, timestamp))
        else:
            # Process current group
            if len(current_group) >= min_touches:
                level = _create_level_from_group(current_group, level_type)
                if level:
                    grouped_levels.append(level)
            
            # Start new group
            current_group = [(price, timestamp)]
    
    # Process last group
    if len(current_group) >= min_touches:
        level = _create_level_from_group(current_group, level_type)
        if level:
            grouped_levels.append(level)
    
    return grouped_levels


def _create_level_from_group(
    group: List[Tuple[float, datetime]], 
    level_type: str
) -> Optional[SupportResistanceLevel]:
    """Create a support/resistance level from a group of price points.
    
    Args:
        group: List of (price, timestamp) tuples.
        level_type: 'support' or 'resistance'.
        
    Returns:
        Optional[SupportResistanceLevel]: Created level or None if invalid.
    """
    if not group:
        return None
    
    try:
        prices = [p for p, _ in group]
        timestamps = [t for _, t in group]
        
        avg_price = sum(prices) / len(prices)
        touches = len(group)
        last_touch = max(timestamps)
        created_at = min(timestamps)
        
        # Calculate strength based on number of touches and price consistency
        price_std = np.std(prices) if len(prices) > 1 else 0
        consistency_factor = max(0, 1 - (price_std / avg_price))
        touch_factor = min(1.0, touches / 5)  # Normalize to max 5 touches
        strength = (consistency_factor + touch_factor) / 2
        
        return SupportResistanceLevel(
            price=avg_price,
            level_type=level_type,
            strength=strength,
            touches=touches,
            last_touch=last_touch,
            created_at=created_at,
        )
        
    except Exception as e:
        logger.error(f"Error creating level from group: {e}")
        return None


def is_price_near_level(
    current_price: float, 
    level: SupportResistanceLevel, 
    tolerance_percent: float = 0.2
) -> bool:
    """Check if current price is near a support/resistance level.
    
    Args:
        current_price: Current stock price.
        level: Support or resistance level.
        tolerance_percent: Price tolerance as percentage.
        
    Returns:
        bool: True if price is near the level.
    """
    tolerance = level.price * (tolerance_percent / 100)
    return abs(current_price - level.price) <= tolerance


def get_trend_direction(df: pd.DataFrame, window: int = 20) -> str:
    """Determine the overall trend direction.
    
    Args:
        df: DataFrame with price data.
        window: Window for trend analysis.
        
    Returns:
        str: 'uptrend', 'downtrend', or 'sideways'.
    """
    if df.empty or len(df) < window:
        return 'sideways'
    
    try:
        recent_data = df.tail(window)
        
        # Calculate slope of closing prices
        x = np.arange(len(recent_data))
        y = recent_data['close'].values
        
        # Linear regression to find slope
        slope = np.polyfit(x, y, 1)[0]
        
        # Determine trend based on slope and magnitude
        price_range = recent_data['close'].max() - recent_data['close'].min()
        avg_price = recent_data['close'].mean()
        
        # Normalize slope by average price
        normalized_slope = slope / avg_price
        
        if normalized_slope > 0.001:  # Threshold for uptrend
            return 'uptrend'
        elif normalized_slope < -0.001:  # Threshold for downtrend
            return 'downtrend'
        else:
            return 'sideways'
            
    except Exception as e:
        logger.error(f"Error determining trend direction: {e}")
        return 'sideways'


def calculate_volatility(df: pd.DataFrame, window: int = 20) -> float:
    """Calculate price volatility (standard deviation of returns).
    
    Args:
        df: DataFrame with price data.
        window: Window for volatility calculation.
        
    Returns:
        float: Volatility as standard deviation of returns.
    """
    if df.empty or len(df) < 2:
        return 0.0
    
    try:
        # Calculate returns
        returns = df['close'].pct_change().dropna()
        
        if len(returns) < window:
            return returns.std()
        
        # Calculate rolling volatility
        volatility = returns.rolling(window=window).std().iloc[-1]
        
        return volatility if not pd.isna(volatility) else 0.0
        
    except Exception as e:
        logger.error(f"Error calculating volatility: {e}")
        return 0.0