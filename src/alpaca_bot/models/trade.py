"""Trade data models for the Alpaca trading bot.

This module defines data classes and models for representing trades,
positions, and trading-related information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TradeType(Enum):
    """Enumeration for trade types."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Enumeration for order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TradeStatus(Enum):
    """Enumeration for trade status."""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Trade:
    """Represents a single trade transaction."""
    
    symbol: str
    trade_type: TradeType
    quantity: float
    price: float
    timestamp: datetime
    order_id: Optional[str] = None
    order_type: OrderType = OrderType.MARKET
    status: TradeStatus = TradeStatus.PENDING
    commission: float = 0.0
    notes: str = ""
    strategy: str = "scalping"
    
    def __post_init__(self) -> None:
        """Post-initialization validation."""
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.price <= 0:
            raise ValueError("Price must be positive")
    
    @property
    def total_value(self) -> float:
        """Calculate total trade value including commission."""
        base_value = self.quantity * self.price
        if self.trade_type == TradeType.BUY:
            return base_value + self.commission
        else:
            return base_value - self.commission
    
    @property
    def is_complete(self) -> bool:
        """Check if trade is complete."""
        return self.status in [TradeStatus.FILLED, TradeStatus.CANCELLED, TradeStatus.REJECTED]
    
    def to_dict(self) -> dict:
        """Convert trade to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'trade_type': self.trade_type.value,
            'quantity': self.quantity,
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'order_id': self.order_id,
            'order_type': self.order_type.value,
            'status': self.status.value,
            'commission': self.commission,
            'notes': self.notes,
            'strategy': self.strategy,
            'total_value': self.total_value,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Trade':
        """Create Trade instance from dictionary."""
        return cls(
            symbol=data['symbol'],
            trade_type=TradeType(data['trade_type']),
            quantity=data['quantity'],
            price=data['price'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            order_id=data.get('order_id'),
            order_type=OrderType(data.get('order_type', 'market')),
            status=TradeStatus(data.get('status', 'pending')),
            commission=data.get('commission', 0.0),
            notes=data.get('notes', ''),
            strategy=data.get('strategy', 'scalping'),
        )


@dataclass
class Position:
    """Represents a current position in a stock."""
    
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    last_updated: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self) -> None:
        """Post-initialization validation."""
        if self.avg_price <= 0:
            raise ValueError("Average price must be positive")
        if self.current_price <= 0:
            raise ValueError("Current price must be positive")
    
    @property
    def is_profitable(self) -> bool:
        """Check if position is currently profitable."""
        return self.unrealized_pnl > 0
    
    @property
    def cost_basis(self) -> float:
        """Calculate the cost basis of the position."""
        return abs(self.quantity) * self.avg_price
    
    def to_dict(self) -> dict:
        """Convert position to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'avg_price': self.avg_price,
            'current_price': self.current_price,
            'market_value': self.market_value,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_percent': self.unrealized_pnl_percent,
            'last_updated': self.last_updated.isoformat(),
            'cost_basis': self.cost_basis,
            'is_profitable': self.is_profitable,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Position':
        """Create Position instance from dictionary."""
        return cls(
            symbol=data['symbol'],
            quantity=data['quantity'],
            avg_price=data['avg_price'],
            current_price=data['current_price'],
            market_value=data['market_value'],
            unrealized_pnl=data['unrealized_pnl'],
            unrealized_pnl_percent=data['unrealized_pnl_percent'],
            last_updated=datetime.fromisoformat(data['last_updated']),
        )


@dataclass
class TradingSession:
    """Represents a trading session with performance metrics."""
    
    start_time: datetime
    end_time: Optional[datetime] = None
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_commission: float = 0.0
    max_drawdown: float = 0.0
    trades: list = field(default_factory=list)
    
    @property
    def is_active(self) -> bool:
        """Check if trading session is currently active."""
        return self.end_time is None
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    @property
    def net_pnl(self) -> float:
        """Calculate net P&L after commissions."""
        return self.total_pnl - self.total_commission
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate session duration in hours."""
        if self.end_time is None:
            end = datetime.now()
        else:
            end = self.end_time
        
        delta = end - self.start_time
        return delta.total_seconds() / 3600
    
    def add_trade(self, trade: Trade) -> None:
        """Add a trade to the session."""
        self.trades.append(trade)
        self.total_trades += 1
        
        if trade.status == TradeStatus.FILLED:
            self.total_commission += trade.commission
            
            # Calculate P&L for completed buy-sell pairs
            # This is simplified - in practice, you'd need more complex logic
            # to match buy/sell pairs and calculate actual P&L
    
    def end_session(self) -> None:
        """End the trading session."""
        self.end_time = datetime.now()
    
    def to_dict(self) -> dict:
        """Convert session to dictionary for serialization."""
        return {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'total_pnl': self.total_pnl,
            'total_commission': self.total_commission,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'net_pnl': self.net_pnl,
            'duration': self.duration,
            'is_active': self.is_active,
            'trades': [trade.to_dict() for trade in self.trades],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TradingSession':
        """Create TradingSession instance from dictionary."""
        session = cls(
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']) if data['end_time'] else None,
            total_trades=data['total_trades'],
            winning_trades=data['winning_trades'],
            losing_trades=data['losing_trades'],
            total_pnl=data['total_pnl'],
            total_commission=data['total_commission'],
            max_drawdown=data['max_drawdown'],
        )
        
        # Reconstruct trades
        session.trades = [Trade.from_dict(trade_data) for trade_data in data.get('trades', [])]
        
        return session