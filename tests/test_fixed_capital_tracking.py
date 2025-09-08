"""Tests for fixed capital tracking functionality."""

import pytest
from unittest.mock import Mock, MagicMock
from src.alpaca_bot.strategies.scalping_strategy import ScalpingStrategy
from src.alpaca_bot.config.settings import Settings
from src.alpaca_bot.models.trade import Trade, TradeType, TradeStatus


class TestFixedCapitalTracking:
    """Test cases for fixed capital tracking functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_alpaca_client = Mock()
        self.mock_account_callback = Mock()
        self.mock_order_callback = Mock()
        
        # Create settings with fixed trade amount enabled
        self.settings = Settings()
        self.settings.fixed_trade_amount_enabled = True
        self.settings.fixed_trade_amount = 100.0
        
        # Create strategy instance
        self.strategy = ScalpingStrategy(
            alpaca_client=self.mock_alpaca_client,
            account_update_callback=self.mock_account_callback,
            order_update_callback=self.mock_order_callback
        )
        
        # Set the settings on the strategy instance
        self.strategy.settings = self.settings
    
    def test_calculate_allocated_capital_empty_positions(self):
        """Test _calculate_allocated_capital with no active positions."""
        self.strategy.active_positions = {}
        
        result = self.strategy._calculate_allocated_capital()
        
        assert result == 0.0
    
    def test_calculate_allocated_capital_with_positions(self):
        """Test _calculate_allocated_capital with active positions."""
        # Create mock trades
        trade1 = Mock()
        trade1.trade_type = TradeType.BUY
        trade1.status = TradeStatus.FILLED
        trade1.quantity = 10.0
        trade1.price = 5.0
        
        trade2 = Mock()
        trade2.trade_type = TradeType.BUY
        trade2.status = TradeStatus.FILLED
        trade2.quantity = 5.0
        trade2.price = 4.0
        
        self.strategy.active_positions = {
            'AAPL': trade1,
            'MSFT': trade2
        }
        
        result = self.strategy._calculate_allocated_capital()
        
        # Expected: (10 * 5) + (5 * 4) = 50 + 20 = 70
        assert result == 70.0
    
    def test_calculate_allocated_capital_with_none_trade(self):
        """Test _calculate_allocated_capital handles None trade objects."""
        self.strategy.active_positions = {
            'AAPL': None,
            'MSFT': Mock()
        }
        
        # Should not raise exception and return 0.0
        result = self.strategy._calculate_allocated_capital()
        assert result == 0.0
    
    def test_calculate_allocated_capital_with_invalid_data(self):
        """Test _calculate_allocated_capital handles invalid trade data."""
        trade = Mock()
        trade.trade_type = TradeType.BUY
        trade.status = TradeStatus.FILLED
        trade.quantity = None  # Invalid data
        trade.price = 5.0
        
        self.strategy.active_positions = {'AAPL': trade}
        
        # Should not raise exception and return 0.0
        result = self.strategy._calculate_allocated_capital()
        assert result == 0.0
    
    def test_calculate_allocated_capital_exception_handling(self):
        """Test _calculate_allocated_capital handles exceptions gracefully."""
        # Create a trade that will cause an exception when accessing attributes
        trade = Mock()
        trade.trade_type = TradeType.BUY
        trade.status = TradeStatus.FILLED
        trade.quantity = Mock(side_effect=Exception("Test exception"))
        
        self.strategy.active_positions = {'AAPL': trade}
        
        # Should not raise exception and return 0.0
        result = self.strategy._calculate_allocated_capital()
        assert result == 0.0


if __name__ == '__main__':
    pytest.main([__file__])