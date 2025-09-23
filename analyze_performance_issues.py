#!/usr/bin/env python3
"""
Performance Analysis Script for Alpaca Trading Bot

This script analyzes:
1. Why the portfolio is gradually losing value
2. Why profit-taking targets are being missed (like META at 0.10%)
3. Current strategy performance and timing issues
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from alpaca_bot.services.alpaca_client import AlpacaClient
from alpaca_bot.config.settings import settings
from alpaca_bot.utils.logging_utils import get_logger

def analyze_portfolio_performance():
    """Analyze current portfolio performance and identify issues."""
    
    logger = get_logger(__name__)
    logger.info("🔍 Starting Portfolio Performance Analysis")
    
    try:
        # Initialize Alpaca client
        client = AlpacaClient()
        logger.info("✅ Connected to Alpaca API")
        
        # Get account information
        account = client.get_account()
        logger.info(f"📊 Account Status: {account.status}")
        logger.info(f"💰 Portfolio Value: ${float(account.portfolio_value):,.2f}")
        logger.info(f"💵 Buying Power: ${float(account.buying_power):,.2f}")
        
        # Calculate day P&L if available
        try:
            if hasattr(account, 'unrealized_pl'):
                logger.info(f"📈 Unrealized P&L: ${float(account.unrealized_pl):,.2f}")
            if hasattr(account, 'unrealized_plpc'):
                logger.info(f"📊 Unrealized P&L %: {float(account.unrealized_plpc)*100:.2f}%")
        except:
            logger.info("📈 P&L information not available in account object")
        
        # Get current positions
        positions = client.get_positions()
        logger.info(f"📍 Active Positions: {len(positions)}")
        
        total_unrealized_pl = 0.0
        total_market_value = 0.0
        
        print("\n" + "="*80)
        print("📊 CURRENT POSITIONS ANALYSIS")
        print("="*80)
        
        for position in positions:
            symbol = position.symbol
            qty = float(position.qty)
            market_value = float(position.market_value)
            unrealized_pl = float(position.unrealized_pl)
            unrealized_plpc = float(position.unrealized_plpc)
            avg_entry_price = float(position.avg_entry_price)
            current_price = float(position.current_price)
            
            total_unrealized_pl += unrealized_pl
            total_market_value += market_value
            
            print(f"\n🏷️  {symbol}")
            print(f"   📊 Quantity: {qty:.4f} shares")
            print(f"   💰 Market Value: ${market_value:,.2f}")
            print(f"   📈 Entry Price: ${avg_entry_price:.2f}")
            print(f"   💹 Current Price: ${current_price:.2f}")
            print(f"   📊 P&L: ${unrealized_pl:,.2f} ({unrealized_plpc*100:.2f}%)")
            
            # Check if close to profit target
            profit_target = settings.take_profit_percentage  # 0.001 = 0.1%
            current_profit_pct = unrealized_plpc
            
            if current_profit_pct >= profit_target * 0.8:  # 80% of target
                print(f"   ⚠️  NEAR PROFIT TARGET! Current: {current_profit_pct*100:.3f}%, Target: {profit_target*100:.3f}%")
                
                # Check recent price movement
                try:
                    # Get recent bars to see price movement
                    end_time = datetime.now()
                    start_time = end_time - timedelta(hours=1)
                    bars = client.get_bars(symbol, '1Min', start=start_time, end=end_time, limit=60)
                    
                    if bars is not None and not bars.empty:
                        recent_high = bars['high'].max()
                        recent_low = bars['low'].min()
                        price_volatility = (recent_high - recent_low) / current_price * 100
                        
                        print(f"   📈 1h High: ${recent_high:.2f}")
                        print(f"   📉 1h Low: ${recent_low:.2f}")
                        print(f"   🌊 Volatility: {price_volatility:.2f}%")
                        
                        # Check if it hit the target recently
                        target_price = avg_entry_price * (1 + profit_target)
                        if recent_high >= target_price:
                            print(f"   🎯 TARGET WAS HIT! Target: ${target_price:.2f}, Recent High: ${recent_high:.2f}")
                            print(f"   ⏰ This suggests a timing issue in profit-taking execution!")
                        
                except Exception as e:
                    print(f"   ❌ Error analyzing recent price movement: {e}")
        
        print(f"\n📊 PORTFOLIO SUMMARY:")
        print(f"   💰 Total Market Value: ${total_market_value:,.2f}")
        print(f"   📈 Total Unrealized P&L: ${total_unrealized_pl:,.2f}")
        print(f"   📊 Overall Performance: {(total_unrealized_pl/total_market_value)*100:.2f}%")
        
        # Analyze strategy settings
        print("\n" + "="*80)
        print("⚙️  STRATEGY SETTINGS ANALYSIS")
        print("="*80)
        
        print(f"🎯 Take Profit Target: {settings.take_profit_percentage*100:.3f}%")
        print(f"🛑 Stop Loss: {settings.stop_loss_percentage*100:.2f}%")
        print(f"💰 Fixed Trade Amount: ${settings.fixed_trade_amount}")
        print(f"🔄 Data Refresh Interval: {settings.data_refresh_interval}s")
        
        # Check if settings are too aggressive
        if settings.take_profit_percentage < 0.005:  # Less than 0.5%
            print(f"⚠️  WARNING: Take profit target is very low ({settings.take_profit_percentage*100:.3f}%)")
            print(f"   This makes it easy to miss due to:")
            print(f"   - Market volatility")
            print(f"   - Execution delays")
            print(f"   - Bid-ask spreads")
            print(f"   💡 Consider increasing to 0.5-1.0% for more reliable execution")
        
        # Check recent orders
        print("\n" + "="*80)
        print("📋 RECENT ORDERS ANALYSIS")
        print("="*80)
        
        try:
            # Get orders from last 24 hours
            end_time = datetime.now()
            start_time = end_time - timedelta(days=1)
            
            orders = client.api.list_orders(
                status='all',
                after=start_time.isoformat(),
                direction='desc',
                limit=50
            )
            
            sell_orders = [order for order in orders if order.side == 'sell']
            buy_orders = [order for order in orders if order.side == 'buy']
            
            print(f"📊 Last 24h Orders: {len(orders)} total ({len(buy_orders)} buy, {len(sell_orders)} sell)")
            
            # Analyze sell orders for profit-taking
            profit_sells = 0
            loss_sells = 0
            
            for order in sell_orders:
                if order.status == 'filled':
                    # Try to find corresponding buy order to calculate P&L
                    symbol = order.symbol
                    fill_price = float(order.filled_avg_price) if order.filled_avg_price else 0
                    
                    print(f"   🔄 SELL {symbol}: ${fill_price:.2f} at {order.filled_at}")
                    
                    # Look for recent buy orders for same symbol
                    recent_buys = [o for o in buy_orders if o.symbol == symbol and o.status == 'filled']
                    if recent_buys:
                        latest_buy = recent_buys[0]
                        buy_price = float(latest_buy.filled_avg_price) if latest_buy.filled_avg_price else 0
                        if buy_price > 0:
                            profit_pct = (fill_price - buy_price) / buy_price * 100
                            print(f"      📈 P&L: {profit_pct:.2f}% (Buy: ${buy_price:.2f})")
                            
                            if profit_pct > 0:
                                profit_sells += 1
                            else:
                                loss_sells += 1
            
            print(f"\n📊 Sell Order Analysis:")
            print(f"   ✅ Profitable sells: {profit_sells}")
            print(f"   ❌ Loss sells: {loss_sells}")
            
            if len(sell_orders) == 0:
                print(f"   ⚠️  NO SELL ORDERS in last 24h - This could indicate:")
                print(f"      - Profit targets are not being hit")
                print(f"      - Execution timing issues")
                print(f"      - Strategy not generating sell signals")
        
        except Exception as e:
            print(f"❌ Error analyzing recent orders: {e}")
        
        # Recommendations
        print("\n" + "="*80)
        print("💡 RECOMMENDATIONS")
        print("="*80)
        
        print("1. 🎯 PROFIT-TAKING IMPROVEMENTS:")
        print("   - Increase take profit target from 0.1% to 0.5-1.0%")
        print("   - Implement trailing stop loss")
        print("   - Use market orders for profit-taking (faster execution)")
        print("   - Reduce monitoring interval for faster response")
        
        print("\n2. 📊 PORTFOLIO PROTECTION:")
        print("   - Review position sizing (currently using fixed $50)")
        print("   - Consider diversification across more symbols")
        print("   - Implement daily loss limits")
        
        print("\n3. ⚡ EXECUTION IMPROVEMENTS:")
        print("   - Reduce data refresh interval from 5s to 1-2s")
        print("   - Use real-time quotes for exit decisions")
        print("   - Implement immediate execution for profit targets")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in performance analysis: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("🚀 Alpaca Trading Bot - Performance Analysis")
    print("=" * 50)
    
    success = analyze_portfolio_performance()
    
    if success:
        print("\n✅ Analysis completed successfully!")
    else:
        print("\n❌ Analysis failed. Check logs for details.")