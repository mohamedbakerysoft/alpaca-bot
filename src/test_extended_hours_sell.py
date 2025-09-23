#!/usr/bin/env python3
"""Test script for extended hours sell orders."""

import logging
import sys
from datetime import datetime

from alpaca_bot.services.alpaca_client import AlpacaClient
from alpaca_bot.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_extended_hours_sell():
    """Test placing a sell order during extended hours."""
    try:
        # Initialize Alpaca client
        client = AlpacaClient()
        
        # Check market status
        is_open = client.is_market_open()
        logger.info(f"Market is currently: {'OPEN' if is_open else 'CLOSED'}")
        
        # Check if extended hours are active (market closed but pre/post market)
        now = datetime.now()
        hour = now.hour
        
        # Extended hours: 4:00 AM - 9:30 AM ET (pre-market) and 4:00 PM - 8:00 PM ET (after-market)
        # Assuming ET timezone for simplicity
        is_extended_hours = (4 <= hour < 9.5) or (16 <= hour < 20)
        logger.info(f"Extended hours active: {is_extended_hours}")
        
        # Get positions
        positions = client.get_positions()
        logger.info(f"Found {len(positions)} positions")
        
        if not positions:
            logger.warning("No positions found to sell")
            return
        
        # Find AAPL position
        aapl_position = None
        for position in positions:
            if position.symbol == 'AAPL':
                aapl_position = position
                break
        
        if not aapl_position:
            logger.warning("No AAPL position found")
            return
        
        logger.info(f"AAPL position: {aapl_position.qty} shares at ${aapl_position.avg_entry_price}")
        
        # Calculate small sell quantity (1% of position)
        total_qty = float(aapl_position.qty)
        sell_qty = max(1, int(total_qty * 0.01))  # At least 1 share
        
        logger.info(f"Planning to sell {sell_qty} shares of AAPL")
        
        # Test different order configurations
        if is_extended_hours:
            logger.info("Testing extended hours sell order...")
            try:
                # Place extended hours sell order (should be DAY limit order)
                order = client.place_order(
                    symbol='AAPL',
                    qty=sell_qty,
                    side='sell',
                    order_type='market',  # Will be converted to limit
                    time_in_force='day',
                    extended_hours=True
                )
                logger.info(f"Extended hours sell order placed successfully: {order.id}")
                logger.info(f"Order type: {order.order_type}, Time in force: {order.time_in_force}")
                if hasattr(order, 'limit_price'):
                    logger.info(f"Limit price: ${order.limit_price}")
                
            except Exception as e:
                logger.error(f"Failed to place extended hours sell order: {e}")
        
        elif not is_open:
            logger.info("Market is closed, testing GTC order...")
            try:
                # Place GTC market order for when market opens
                order = client.place_order(
                    symbol='AAPL',
                    qty=sell_qty,
                    side='sell',
                    order_type='market',
                    time_in_force='gtc',
                    extended_hours=False
                )
                logger.info(f"GTC sell order placed successfully: {order.id}")
                logger.info(f"Order type: {order.order_type}, Time in force: {order.time_in_force}")
                
            except Exception as e:
                logger.error(f"Failed to place GTC sell order: {e}")
        
        else:
            logger.info("Market is open, testing regular market order...")
            try:
                # Place regular market order
                order = client.place_order(
                    symbol='AAPL',
                    qty=sell_qty,
                    side='sell',
                    order_type='market',
                    time_in_force='day',
                    extended_hours=False
                )
                logger.info(f"Regular sell order placed successfully: {order.id}")
                logger.info(f"Order type: {order.order_type}, Time in force: {order.time_in_force}")
                
            except Exception as e:
                logger.error(f"Failed to place regular sell order: {e}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_extended_hours_sell()