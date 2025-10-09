#!/usr/bin/env python3
"""Test script for sell signal when stock gains 43%."""

import logging
import sys
from datetime import datetime, timedelta
from typing import Optional

from alpaca_bot.services.alpaca_client import AlpacaClient
from alpaca_bot.strategies.safe_strategy import SafeStrategy
from alpaca_bot.models.stock import StockData, StockQuote, TechnicalIndicators
from alpaca_bot.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_mock_stock_data(symbol: str, current_price: float, entry_price: float) -> StockData:
    """Create mock stock data for testing."""
    # Create quote
    quote = StockQuote(
        symbol=symbol,
        bid=current_price - 0.01,
        ask=current_price + 0.01,
        bid_size=100,
        ask_size=100,
        timestamp=datetime.now()
    )
    
    # Create technical indicators
    indicators = TechnicalIndicators(
        symbol=symbol,
        timestamp=datetime.now(),
        sma_20=current_price * 0.95,
        sma_50=current_price * 0.90,
        rsi=65.0,
        macd=0.5,
        macd_signal=0.3,
        macd_histogram=0.2,
        bollinger_upper=current_price * 1.05,
        bollinger_lower=current_price * 0.95,
        bollinger_middle=current_price
    )
    
    return StockData(
        symbol=symbol,
        company_name=f"{symbol} Inc.",
        current_quote=quote,
        technical_indicators=indicators
    )

def test_sell_signal_43_percent():
    """Test sell signal generation when stock gains 43%."""
    try:
        # Initialize Alpaca client and strategy
        client = AlpacaClient()
        strategy = SafeStrategy(client)
        
        logger.info("Testing sell signal for 43% gain scenario...")
        
        # Test symbol
        symbol = 'AAPL'
        
        # Simulate a position with 43% gain
        entry_price = 150.0
        current_price = entry_price * 1.43  # 43% gain
        
        logger.info(f"Testing {symbol}:")
        logger.info(f"Entry price: ${entry_price:.2f}")
        logger.info(f"Current price: ${current_price:.2f}")
        logger.info(f"Gain: {((current_price / entry_price) - 1) * 100:.1f}%")
        
        # Create mock stock data
        stock_data = create_mock_stock_data(symbol, current_price, entry_price)
        
        # Mock position data in strategy - need to import Trade class
        from alpaca_bot.models.trade import Trade, TradeType, TradeStatus
        
        mock_trade = Trade(
            symbol=symbol,
            trade_type=TradeType.BUY,
            quantity=100,
            price=entry_price,
            timestamp=datetime.now() - timedelta(days=1),
            status=TradeStatus.FILLED
        )
        
        strategy.active_positions[symbol] = mock_trade
        
        logger.info(f"Position: {strategy.active_positions[symbol]}")
        
        # Test sell opportunity analysis
        logger.info("\n--- Testing _analyze_sell_opportunity ---")
        sell_signal = strategy._analyze_sell_opportunity(stock_data)
        
        if sell_signal:
            logger.info(f"✅ Sell signal generated!")
            logger.info(f"Action: {sell_signal.action}")
            logger.info(f"Symbol: {sell_signal.symbol}")
            logger.info(f"Price: ${sell_signal.price:.2f}")
            logger.info(f"Confidence: {sell_signal.confidence:.2f}")
            logger.info(f"Reason: {sell_signal.reason}")
        else:
            logger.warning("❌ No sell signal generated")
        
        # Test full signal generation
        logger.info("\n--- Testing generate_signals ---")
        signals = strategy.generate_signals([stock_data])
        
        if signals:
            logger.info(f"✅ {len(signals)} signal(s) generated from generate_signals")
            for i, signal in enumerate(signals):
                logger.info(f"Signal {i+1}:")
                if hasattr(signal, 'action'):
                    logger.info(f"  Action: {signal.action}")
                    logger.info(f"  Symbol: {signal.symbol}")
                    logger.info(f"  Price: ${signal.price:.2f}")
                    logger.info(f"  Confidence: {signal.confidence:.2f}")
                    logger.info(f"  Reason: {signal.reason}")
                else:
                    logger.info(f"  Signal: {signal}")
        else:
            logger.warning("❌ No signals generated from generate_signals")
        
        # Test different gain scenarios
        logger.info("\n--- Testing different gain scenarios ---")
        test_gains = [0.10, 0.20, 0.30, 0.40, 0.43, 0.45, 0.50, 0.60]
        
        for gain in test_gains:
            test_price = entry_price * (1 + gain)
            test_stock_data = create_mock_stock_data(symbol, test_price, entry_price)
            
            # Update position price for testing
            strategy.active_positions[symbol].price = entry_price
            
            sell_signal = strategy._analyze_sell_opportunity(test_stock_data)
            
            status = "✅ SELL" if sell_signal else "❌ HOLD"
            logger.info(f"Gain {gain*100:5.1f}% (${test_price:6.2f}): {status}")
        
        logger.info("\n--- Test completed successfully ---")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_sell_signal_43_percent()