"""Extended hours trading monitor for the Alpaca trading bot.

This module provides monitoring and safety features for extended hours trading:
- Volume and liquidity monitoring
- Spread monitoring
- Risk management adjustments
- Performance tracking
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pytz
from dataclasses import dataclass

from ..config.settings import settings
from .market_utils import MarketHours


@dataclass
class ExtendedHoursMetrics:
    """Extended hours trading metrics."""
    symbol: str
    timestamp: datetime
    volume: int
    spread: float
    volatility: float
    liquidity_score: float
    risk_level: str  # 'LOW', 'MEDIUM', 'HIGH'


class ExtendedHoursMonitor:
    """Monitor for extended hours trading safety and performance."""
    
    def __init__(self):
        """Initialize extended hours monitor."""
        self.logger = logging.getLogger(__name__)
        self.eastern_tz = pytz.timezone('US/Eastern')
        
        # Monitoring thresholds
        self.min_volume_threshold = 10000  # Minimum volume for safe trading
        self.max_spread_threshold = 0.05   # Maximum spread (5%)
        self.high_volatility_threshold = 0.03  # High volatility threshold (3%)
        
        # Metrics storage
        self.metrics_history: Dict[str, List[ExtendedHoursMetrics]] = {}
        self.risk_alerts: List[str] = []
        
    def is_safe_for_extended_trading(self, symbol: str, current_price: float, 
                                   volume: int, bid: float, ask: float) -> Tuple[bool, str]:
        """Check if it's safe to trade a symbol during extended hours.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            volume: Current volume
            bid: Current bid price
            ask: Current ask price
            
        Returns:
            Tuple of (is_safe, reason)
        """
        if not getattr(settings, 'extended_hours_enabled', False):
            return False, "Extended hours trading is disabled"
        
        if not MarketHours.is_extended_hours():
            return True, "Regular trading hours"
        
        # Check volume
        if volume < self.min_volume_threshold:
            return False, f"Low volume ({volume:,} < {self.min_volume_threshold:,})"
        
        # Check spread
        if bid > 0 and ask > 0:
            spread = (ask - bid) / current_price
            if spread > self.max_spread_threshold:
                return False, f"Wide spread ({spread:.2%} > {self.max_spread_threshold:.2%})"
        
        # Check if symbol is in high-risk list
        high_risk_symbols = getattr(settings, 'extended_hours_restricted_symbols', [])
        if symbol in high_risk_symbols:
            return False, f"Symbol {symbol} is restricted during extended hours"
        
        return True, "Safe for extended hours trading"
    
    def calculate_liquidity_score(self, symbol: str, volume: int, 
                                bid: float, ask: float, current_price: float) -> float:
        """Calculate liquidity score for extended hours trading.
        
        Args:
            symbol: Stock symbol
            volume: Current volume
            bid: Current bid price
            ask: Current ask price
            current_price: Current stock price
            
        Returns:
            Liquidity score (0-100)
        """
        score = 0.0
        
        # Volume component (40% weight)
        volume_score = min(volume / self.min_volume_threshold, 5.0) * 20
        score += volume_score * 0.4
        
        # Spread component (30% weight)
        if bid > 0 and ask > 0 and current_price > 0:
            spread = (ask - bid) / current_price
            spread_score = max(0, (self.max_spread_threshold - spread) / self.max_spread_threshold) * 100
            score += spread_score * 0.3
        
        # Price stability component (30% weight)
        # This would require historical data, simplified for now
        stability_score = 50  # Default neutral score
        score += stability_score * 0.3
        
        return min(score, 100.0)
    
    def calculate_liquidity_score(self, symbol: str) -> float:
        """Calculate liquidity score for extended hours trading using stored metrics.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Liquidity score (0-100)
        """
        # Check if we have recent metrics for this symbol
        if symbol not in self.metrics_history or not self.metrics_history[symbol]:
            return 0.0  # No data available
        
        latest_metrics = self.metrics_history[symbol][-1]
        
        # Check if metrics are recent (within last 5 minutes)
        time_diff = datetime.now(self.eastern_tz) - latest_metrics.timestamp
        if time_diff.total_seconds() > 300:  # 5 minutes
            return 0.0  # Stale data
        
        return latest_metrics.liquidity_score
    
    def get_risk_level(self, liquidity_score: float, volatility: float) -> str:
        """Determine risk level based on liquidity and volatility.
        
        Args:
            liquidity_score: Liquidity score (0-100)
            volatility: Current volatility
            
        Returns:
            Risk level string
        """
        if liquidity_score >= 70 and volatility < 0.02:
            return 'LOW'
        elif liquidity_score >= 50 and volatility < self.high_volatility_threshold:
            return 'MEDIUM'
        else:
            return 'HIGH'
    
    def update_metrics(self, symbol: str, current_price: float, volume: int,
                      bid: float, ask: float, volatility: float = 0.0):
        """Update metrics for a symbol.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            volume: Current volume
            bid: Current bid price
            ask: Current ask price
            volatility: Current volatility
        """
        if not MarketHours.is_extended_hours():
            return
        
        # Calculate metrics
        spread = (ask - bid) / current_price if bid > 0 and ask > 0 and current_price > 0 else 0
        liquidity_score = self.calculate_liquidity_score(symbol, volume, bid, ask, current_price)
        risk_level = self.get_risk_level(liquidity_score, volatility)
        
        # Create metrics object
        metrics = ExtendedHoursMetrics(
            symbol=symbol,
            timestamp=datetime.now(self.eastern_tz),
            volume=volume,
            spread=spread,
            volatility=volatility,
            liquidity_score=liquidity_score,
            risk_level=risk_level
        )
        
        # Store metrics
        if symbol not in self.metrics_history:
            self.metrics_history[symbol] = []
        
        self.metrics_history[symbol].append(metrics)
        
        # Keep only last 100 entries per symbol
        if len(self.metrics_history[symbol]) > 100:
            self.metrics_history[symbol] = self.metrics_history[symbol][-100:]
        
        # Generate alerts for high-risk conditions
        if risk_level == 'HIGH':
            alert = f"HIGH RISK: {symbol} - Liquidity: {liquidity_score:.1f}, Volatility: {volatility:.2%}"
            if alert not in self.risk_alerts:
                self.risk_alerts.append(alert)
                self.logger.warning(alert)
    
    def get_extended_hours_summary(self) -> Dict:
        """Get summary of extended hours trading metrics.
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.metrics_history:
            return {"status": "No extended hours data available"}
        
        summary = {
            "total_symbols_monitored": len(self.metrics_history),
            "current_session": self.market_hours.get_trading_session_type(),
            "risk_alerts": len(self.risk_alerts),
            "symbols_by_risk": {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        }
        
        # Analyze latest metrics for each symbol
        for symbol, metrics_list in self.metrics_history.items():
            if metrics_list:
                latest_metrics = metrics_list[-1]
                summary["symbols_by_risk"][latest_metrics.risk_level] += 1
        
        return summary
    
    def should_reduce_position_size(self, symbol: str) -> Tuple[bool, float]:
        """Check if position size should be reduced for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Tuple of (should_reduce, reduction_factor)
        """
        if symbol not in self.metrics_history or not self.metrics_history[symbol]:
            return True, 0.5  # Default reduction for unknown symbols
        
        latest_metrics = self.metrics_history[symbol][-1]
        
        if latest_metrics.risk_level == 'HIGH':
            return True, 0.3  # Reduce to 30% of normal size
        elif latest_metrics.risk_level == 'MEDIUM':
            return True, 0.6  # Reduce to 60% of normal size
        else:
            return False, 1.0  # No reduction needed
    
    def get_recommended_limits(self, symbol: str) -> Dict[str, float]:
        """Get recommended trading limits for extended hours.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with recommended limits
        """
        base_limits = {
            'max_position_size': getattr(settings, 'extended_hours_max_position_size', 1000),
            'stop_loss_pct': getattr(settings, 'extended_hours_stop_loss_percentage', 0.02),
            'take_profit_pct': getattr(settings, 'extended_hours_take_profit_percentage', 0.03)
        }
        
        if symbol not in self.metrics_history or not self.metrics_history[symbol]:
            return base_limits
        
        latest_metrics = self.metrics_history[symbol][-1]
        
        # Adjust limits based on risk level
        if latest_metrics.risk_level == 'HIGH':
            base_limits['max_position_size'] *= 0.5
            base_limits['stop_loss_pct'] *= 0.7  # Tighter stop loss
            base_limits['take_profit_pct'] *= 0.8  # Lower take profit
        elif latest_metrics.risk_level == 'MEDIUM':
            base_limits['max_position_size'] *= 0.75
            base_limits['stop_loss_pct'] *= 0.85
            base_limits['take_profit_pct'] *= 0.9
        
        return base_limits
    
    def cleanup_old_data(self, hours_to_keep: int = 24):
        """Clean up old metrics data.
        
        Args:
            hours_to_keep: Number of hours of data to keep
        """
        cutoff_time = datetime.now(self.eastern_tz) - timedelta(hours=hours_to_keep)
        
        for symbol in list(self.metrics_history.keys()):
            self.metrics_history[symbol] = [
                m for m in self.metrics_history[symbol] 
                if m.timestamp > cutoff_time
            ]
            
            # Remove empty entries
            if not self.metrics_history[symbol]:
                del self.metrics_history[symbol]
        
        # Clean up old alerts
        self.risk_alerts = self.risk_alerts[-50:]  # Keep last 50 alerts
    
    def is_trading_safe(self, symbol: str) -> tuple[bool, str]:
        """Check if trading is safe for the given symbol during extended hours.
        
        Args:
            symbol: Stock symbol to check
            
        Returns:
            tuple[bool, str]: (is_safe, reason)
        """
        if not getattr(settings, 'extended_hours_enabled', False):
            return True, "Extended hours trading disabled"
        
        if not MarketHours.is_extended_hours():
            return True, "Regular trading hours"
        
        # Check if we have recent metrics for this symbol
        if symbol not in self.metrics_history or not self.metrics_history[symbol]:
            return False, "No recent data available"
        
        latest_metrics = self.metrics_history[symbol][-1]
        
        # Check if metrics are recent (within last 5 minutes)
        time_diff = datetime.now(self.eastern_tz) - latest_metrics.timestamp
        if time_diff.total_seconds() > 300:  # 5 minutes
            return False, "Data is stale (>5 minutes old)"
        
        # Check risk level
        if latest_metrics.risk_level == 'HIGH':
            return False, f"High risk level ({latest_metrics.risk_level})"
        
        # Check volume and liquidity
        if latest_metrics.volume < self.min_volume_threshold:
            return False, f"Low volume ({latest_metrics.volume:,} < {self.min_volume_threshold:,})"
        
        if latest_metrics.liquidity_score < 50:  # Minimum liquidity score
            return False, f"Low liquidity score ({latest_metrics.liquidity_score:.1f} < 50)"
        
        return True, f"Safe for trading (Risk: {latest_metrics.risk_level}, Volume: {latest_metrics.volume:,})"
    
    def determine_risk_level(self, symbol: str) -> str:
        """Determine risk level for extended hours trading.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            str: Risk level ('LOW', 'MEDIUM', 'HIGH')
        """
        # Check if we have recent metrics for this symbol
        if symbol not in self.metrics_history or not self.metrics_history[symbol]:
            return 'HIGH'  # No data available, assume high risk
        
        latest_metrics = self.metrics_history[symbol][-1]
        
        # Check if metrics are recent (within last 5 minutes)
        time_diff = datetime.now(self.eastern_tz) - latest_metrics.timestamp
        if time_diff.total_seconds() > 300:  # 5 minutes
            return 'HIGH'  # Stale data, assume high risk
        
        return latest_metrics.risk_level
    
    def get_extended_hours_summary(self) -> Dict[str, Any]:
        """Get summary of extended hours trading metrics.
        
        Returns:
            Dict containing summary of all tracked symbols
        """
        summary = {}
        current_time = datetime.now(self.eastern_tz)
        
        for symbol, metrics_list in self.metrics_history.items():
            if not metrics_list:
                continue
                
            latest_metrics = metrics_list[-1]
            
            # Check if metrics are recent (within last 5 minutes)
            time_diff = current_time - latest_metrics.timestamp
            is_recent = time_diff.total_seconds() <= 300
            
            summary[symbol] = {
                'timestamp': latest_metrics.timestamp.isoformat(),
                'volume': latest_metrics.volume,
                'spread': latest_metrics.spread,
                'volatility': latest_metrics.volatility,
                'liquidity_score': latest_metrics.liquidity_score,
                'risk_level': latest_metrics.risk_level,
                'is_recent': is_recent,
                'age_seconds': time_diff.total_seconds()
            }
        
        return summary


# Global extended hours monitor instance
extended_hours_monitor = ExtendedHoursMonitor()