#!/usr/bin/env python3
"""
Simple test script to validate Alpaca API credentials.
This script makes a basic API call to verify if the credentials work.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from decouple import config
    import alpaca_trade_api as tradeapi
    from alpaca_trade_api.rest import APIError
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please install required dependencies: pip install python-decouple alpaca-trade-api")
    sys.exit(1)


def test_alpaca_credentials():
    """Test Alpaca API credentials with a simple account request."""
    print("🔍 Testing Alpaca API Credentials...")
    print("=" * 50)
    
    # Load credentials from .env file
    try:
        api_key = config("ALPACA_API_KEY", default="")
        secret_key = config("ALPACA_SECRET_KEY", default="")
        base_url = config("ALPACA_BASE_URL", default="https://paper-api.alpaca.markets")
        
        print(f"📍 API Key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else 'INVALID'}")
        print(f"📍 Base URL: {base_url}")
        
        if not api_key or not secret_key:
            print("❌ ERROR: API credentials are missing!")
            print("Please check your .env file and ensure ALPACA_API_KEY and ALPACA_SECRET_KEY are set.")
            return False
            
    except Exception as e:
        print(f"❌ ERROR loading credentials: {e}")
        return False
    
    # Initialize Alpaca API client
    try:
        print("\n🔗 Connecting to Alpaca API...")
        api = tradeapi.REST(
            key_id=api_key,
            secret_key=secret_key,
            base_url=base_url,
            api_version='v2'
        )
        
        # Test 1: Get account information
        print("\n📊 Test 1: Getting account information...")
        account = api.get_account()
        
        print(f"✅ SUCCESS: Connected to Alpaca API!")
        print(f"   Account ID: {account.id}")
        print(f"   Account Status: {account.status}")
        print(f"   Account Type: {'Paper Trading' if 'paper' in base_url else 'Live Trading'}")
        print(f"   Buying Power: ${float(account.buying_power):,.2f}")
        print(f"   Cash: ${float(account.cash):,.2f}")
        print(f"   Portfolio Value: ${float(account.portfolio_value):,.2f}")
        
        # Test 2: Check market status
        print("\n🕐 Test 2: Checking market status...")
        clock = api.get_clock()
        print(f"   Market Open: {'Yes' if clock.is_open else 'No'}")
        print(f"   Next Open: {clock.next_open}")
        print(f"   Next Close: {clock.next_close}")
        
        # Test 3: Get a simple stock quote
        print("\n📈 Test 3: Getting stock quote for AAPL...")
        try:
            latest_trade = api.get_latest_trade('AAPL')
            print(f"   AAPL Latest Price: ${latest_trade.price}")
            print(f"   Trade Time: {latest_trade.timestamp}")
        except Exception as e:
            print(f"   ⚠️  Warning: Could not get stock quote: {e}")
        
        print("\n🎉 ALL TESTS PASSED! Your Alpaca API credentials are working correctly.")
        return True
        
    except APIError as e:
        print(f"\n❌ API ERROR: {e}")
        if e.status_code == 401:
            print("   This usually means your API key or secret is incorrect.")
        elif e.status_code == 403:
            print("   This usually means your account doesn't have permission for this operation.")
            print("   Make sure your account is approved for trading.")
        elif e.status_code == 429:
            print("   Rate limit exceeded. Please wait and try again.")
        else:
            print(f"   HTTP Status Code: {e.status_code}")
        return False
        
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        print("   Please check your internet connection and try again.")
        return False


if __name__ == "__main__":
    print("Alpaca API Credentials Test")
    print("===========================\n")
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ ERROR: .env file not found!")
        print("Please create a .env file with your Alpaca API credentials.")
        sys.exit(1)
    
    success = test_alpaca_credentials()
    
    if success:
        print("\n✅ Your credentials are valid and ready to use with the trading bot!")
        sys.exit(0)
    else:
        print("\n❌ Credential test failed. Please check your API keys and try again.")
        sys.exit(1)