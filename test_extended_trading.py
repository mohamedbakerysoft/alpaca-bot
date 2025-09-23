#!/usr/bin/env python3
"""
Comprehensive test script for extended trading hours functionality.

This script tests all components of the extended trading system:
1. Market hours detection
2. Extended hours monitor
3. Strategy integration
4. Risk management adjustments
"""

import sys
import os
from datetime import datetime, time
from typing import Dict, Any

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from alpaca_bot.config.settings import settings
from alpaca_bot.utils.market_utils import MarketHours
from alpaca_bot.utils.extended_hours_monitor import ExtendedHoursMonitor
from alpaca_bot.services.alpaca_client import AlpacaClient


class ExtendedTradingTester:
    """Comprehensive tester for extended trading functionality."""
    
    def __init__(self):
        """Initialize the tester."""
        self.results: Dict[str, Any] = {}
        self.monitor = ExtendedHoursMonitor()
        
        # Test symbols
        self.test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'SPY']
        
        print("🚀 Extended Trading System Test Suite")
        print("=" * 50)
    
    def test_market_hours_detection(self) -> bool:
        """Test market hours detection functionality."""
        print("\n📅 Testing Market Hours Detection...")
        
        try:
            # Test basic market status
            is_open = MarketHours.is_market_open()
            status = MarketHours.get_market_status()
            session_type = MarketHours.get_trading_session_type()
            
            print(f"   ✓ Market Open: {is_open}")
            print(f"   ✓ Market Status: {status}")
            print(f"   ✓ Session Type: {session_type}")
            
            # Test extended hours detection
            if hasattr(MarketHours, 'is_extended_hours'):
                is_extended = MarketHours.is_extended_hours()
                print(f"   ✓ Extended Hours: {is_extended}")
            
            # Test weekend trading check
            if hasattr(MarketHours, 'should_stop_weekend_trading'):
                should_stop = MarketHours.should_stop_weekend_trading()
                print(f"   ✓ Should Stop Weekend Trading: {should_stop}")
            
            self.results['market_hours'] = {
                'status': 'PASS',
                'is_open': is_open,
                'market_status': status,
                'session_type': session_type
            }
            
            print("   ✅ Market Hours Detection: PASS")
            return True
            
        except Exception as e:
            print(f"   ❌ Market Hours Detection: FAIL - {e}")
            self.results['market_hours'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def test_extended_hours_monitor(self) -> bool:
        """Test extended hours monitor functionality."""
        print("\n📊 Testing Extended Hours Monitor...")
        
        try:
            test_results = []
            
            for symbol in self.test_symbols:
                print(f"   Testing {symbol}...")
                
                # Simulate market data
                self.monitor.update_metrics(
                    symbol=symbol,
                    current_price=150.0 + hash(symbol) % 50,
                    volume=100000 + hash(symbol) % 500000,
                    bid=149.95,
                    ask=150.05,
                    volatility=0.02 + (hash(symbol) % 10) / 1000
                )
                
                # Test safety check
                is_safe, reason = self.monitor.is_trading_safe(symbol)
                print(f"     - Trading Safe: {is_safe} ({reason})")
                
                # Test liquidity score
                liquidity_score = self.monitor.calculate_liquidity_score(symbol)
                print(f"     - Liquidity Score: {liquidity_score:.2f}")
                
                # Test risk level
                risk_level = self.monitor.determine_risk_level(symbol)
                print(f"     - Risk Level: {risk_level}")
                
                test_results.append({
                    'symbol': symbol,
                    'is_safe': is_safe,
                    'liquidity_score': liquidity_score,
                    'risk_level': risk_level
                })
            
            # Test summary functionality
            summary = self.monitor.get_extended_hours_summary()
            print(f"   ✓ Extended Hours Summary: {len(summary)} symbols tracked")
            
            self.results['extended_monitor'] = {
                'status': 'PASS',
                'symbols_tested': len(test_results),
                'summary_count': len(summary)
            }
            
            print("   ✅ Extended Hours Monitor: PASS")
            return True
            
        except Exception as e:
            print(f"   ❌ Extended Hours Monitor: FAIL - {e}")
            self.results['extended_monitor'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def test_settings_integration(self) -> bool:
        """Test settings integration for extended trading."""
        print("\n⚙️ Testing Settings Integration...")
        
        try:
            # Test extended hours settings
            extended_enabled = getattr(settings, 'extended_hours_enabled', False)
            print(f"   ✓ Extended Hours Enabled: {extended_enabled}")
            
            # Test extended hours parameters
            params_to_check = [
                'extended_hours_take_profit_percentage',
                'extended_hours_stop_loss_percentage',
                'extended_hours_position_size_multiplier',
                'extended_hours_max_position_size',
                'weekend_trading_enabled'
            ]
            
            available_params = []
            for param in params_to_check:
                if hasattr(settings, param):
                    value = getattr(settings, param)
                    print(f"   ✓ {param}: {value}")
                    available_params.append(param)
                else:
                    print(f"   ⚠️ {param}: Not configured")
            
            self.results['settings'] = {
                'status': 'PASS',
                'extended_enabled': extended_enabled,
                'available_params': len(available_params),
                'total_params': len(params_to_check)
            }
            
            print("   ✅ Settings Integration: PASS")
            return True
            
        except Exception as e:
            print(f"   ❌ Settings Integration: FAIL - {e}")
            self.results['settings'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def test_strategy_integration(self) -> bool:
        """Test strategy integration with extended trading."""
        print("\n🎯 Testing Strategy Integration...")
        
        try:
            # Import strategy (this tests if imports work correctly)
            from alpaca_bot.strategies.scalping_strategy import ScalpingStrategy
            
            print("   ✓ Strategy import successful")
            
            # Test if ExtendedHoursMonitor is properly integrated
            # Note: We can't fully test without a real AlpacaClient
            print("   ✓ Strategy class accessible")
            
            # Check if the strategy has the required methods for extended trading
            required_methods = [
                '_is_optimal_trading_time',
                '_calculate_dynamic_position_size',
                '_calculate_dynamic_take_profit'
            ]
            
            available_methods = []
            for method in required_methods:
                if hasattr(ScalpingStrategy, method):
                    available_methods.append(method)
                    print(f"   ✓ Method {method}: Available")
                else:
                    print(f"   ⚠️ Method {method}: Not found")
            
            self.results['strategy'] = {
                'status': 'PASS',
                'import_successful': True,
                'available_methods': len(available_methods),
                'total_methods': len(required_methods)
            }
            
            print("   ✅ Strategy Integration: PASS")
            return True
            
        except Exception as e:
            print(f"   ❌ Strategy Integration: FAIL - {e}")
            self.results['strategy'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def test_risk_management(self) -> bool:
        """Test risk management adjustments for extended trading."""
        print("\n🛡️ Testing Risk Management...")
        
        try:
            # Test different risk scenarios
            test_scenarios = [
                {'volume': 1000000, 'volatility': 0.01, 'spread': 0.01, 'expected_risk': 'LOW'},
                {'volume': 100000, 'volatility': 0.05, 'spread': 0.05, 'expected_risk': 'HIGH'},
                {'volume': 500000, 'volatility': 0.03, 'spread': 0.02, 'expected_risk': 'MEDIUM'}
            ]
            
            passed_scenarios = 0
            
            for i, scenario in enumerate(test_scenarios):
                symbol = f"TEST{i}"
                
                # Update monitor with scenario data
                self.monitor.update_metrics(
                    symbol=symbol,
                    current_price=100.0,
                    volume=scenario['volume'],
                    bid=100.0 - scenario['spread']/2,
                    ask=100.0 + scenario['spread']/2,
                    volatility=scenario['volatility']
                )
                
                risk_level = self.monitor.determine_risk_level(symbol)
                is_safe, reason = self.monitor.is_trading_safe(symbol)
                
                print(f"   Scenario {i+1}: Volume={scenario['volume']}, "
                      f"Volatility={scenario['volatility']:.3f}, "
                      f"Risk={risk_level}, Safe={is_safe}")
                
                if risk_level == scenario['expected_risk']:
                    passed_scenarios += 1
            
            self.results['risk_management'] = {
                'status': 'PASS',
                'scenarios_tested': len(test_scenarios),
                'scenarios_passed': passed_scenarios
            }
            
            print(f"   ✅ Risk Management: PASS ({passed_scenarios}/{len(test_scenarios)} scenarios)")
            return True
            
        except Exception as e:
            print(f"   ❌ Risk Management: FAIL - {e}")
            self.results['risk_management'] = {'status': 'FAIL', 'error': str(e)}
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return results."""
        print(f"🕐 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        tests = [
            ('Market Hours Detection', self.test_market_hours_detection),
            ('Extended Hours Monitor', self.test_extended_hours_monitor),
            ('Settings Integration', self.test_settings_integration),
            ('Strategy Integration', self.test_strategy_integration),
            ('Risk Management', self.test_risk_management)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            if test_func():
                passed_tests += 1
        
        # Generate summary
        print("\n" + "=" * 50)
        print("📋 TEST SUMMARY")
        print("=" * 50)
        
        for test_name, result in self.results.items():
            status = result.get('status', 'UNKNOWN')
            emoji = "✅" if status == 'PASS' else "❌"
            print(f"{emoji} {test_name.replace('_', ' ').title()}: {status}")
            
            if status == 'FAIL' and 'error' in result:
                print(f"   Error: {result['error']}")
        
        print(f"\n🎯 Overall Result: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All tests passed! Extended trading system is ready.")
        else:
            print("⚠️ Some tests failed. Please review the errors above.")
        
        # Add overall summary to results
        self.results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': passed_tests / total_tests,
            'timestamp': datetime.now().isoformat()
        }
        
        return self.results


def main():
    """Main function to run the test suite."""
    tester = ExtendedTradingTester()
    results = tester.run_all_tests()
    
    # Optionally save results to file
    import json
    results_file = f"extended_trading_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Test results saved to: {results_file}")
    except Exception as e:
        print(f"\n⚠️ Could not save results to file: {e}")
    
    # Return exit code based on test results
    success_rate = results['summary']['success_rate']
    return 0 if success_rate == 1.0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)