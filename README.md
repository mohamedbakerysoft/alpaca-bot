# Alpaca Trading Bot

A Python desktop application for automated stock trading using the Alpaca API. This application implements a scalping strategy with real-time market data analysis, risk management, and an intuitive GUI interface.

## Features

### Core Functionality
- **Automated Scalping Strategy**: Identifies support/resistance levels and executes trades automatically
- **Real-time Market Data**: Live price feeds and technical analysis
- **Risk Management**: Configurable position sizing, stop-loss, and take-profit settings
- **Manual Trading**: Override automation with manual trade execution
- **Trade Logging**: Comprehensive logging of all trading activities

### User Interface
- **Start/Stop Controls**: Easy trading automation control
- **Stock Selection**: Manual selection via dropdown or auto-selection based on criteria
- **Real-time Display**: Live performance metrics and trading statistics
- **Configuration Panel**: Adjust strategy parameters and risk settings
- **Emergency Controls**: Quick position closure and order cancellation

### Technical Features
- **Secure API Integration**: Environment-based credential management
- **Error Handling**: Robust error handling for network and API issues
- **Performance Monitoring**: Real-time P&L tracking and trade statistics
- **Modular Architecture**: Clean separation of concerns for maintainability

## Installation

### Prerequisites
- Python 3.8 or higher
- Alpaca Trading Account (Paper or Live)
- API Keys from Alpaca

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd alpaca-bot
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   # For production use
   pip install -r requirements/prod.txt
   
   # For development
   pip install -r requirements/dev.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` file with your Alpaca API credentials:
   ```env
   ALPACA_API_KEY=your_api_key_here
   ALPACA_SECRET_KEY=your_secret_key_here
   ALPACA_BASE_URL=https://paper-api.alpaca.markets/v2  # Paper trading
   # ALPACA_BASE_URL=https://api.alpaca.markets/v2      # Live trading
   ```

## Usage

### Running the Application

```bash
# From the project root
python -m src.alpaca_bot.main

# Or using the entry point (after installation)
alpaca-bot
```

### Configuration

The application can be configured through:

1. **Environment Variables** (`.env` file):
   - API credentials
   - Trading mode (paper/live)
   - Base URLs

2. **GUI Settings Panel**:
   - Strategy parameters
   - Risk management settings
   - Position sizing

3. **Configuration File** (`src/alpaca_bot/config/settings.py`):
   - Default values
   - Application settings

### Trading Strategy

The scalping strategy implements:

1. **Technical Analysis**:
   - Support/Resistance level identification
   - RSI (Relative Strength Index)
   - Bollinger Bands
   - Moving averages

2. **Entry Signals**:
   - Price approaching support levels
   - RSI oversold conditions
   - Volume confirmation

3. **Exit Signals**:
   - Price approaching resistance levels
   - RSI overbought conditions
   - Stop-loss/Take-profit triggers

### Risk Management

- **Position Sizing**: Configurable maximum position size
- **Stop Loss**: Automatic stop-loss orders
- **Take Profit**: Profit-taking at resistance levels
- **Daily Limits**: Maximum daily loss and trade count limits
- **Risk per Trade**: Percentage-based risk management

## Project Structure

```
alpaca-bot/
├── src/
│   └── alpaca_bot/
│       ├── __init__.py
│       ├── main.py              # Application entry point
│       ├── config/
│       │   └── settings.py      # Configuration management
│       ├── models/
│       │   ├── trade.py         # Trade data models
│       │   └── stock.py         # Stock data models
│       ├── services/
│       │   └── alpaca_client.py # Alpaca API client
│       ├── strategies/
│       │   └── scalping_strategy.py # Trading strategy
│       ├── utils/
│       │   ├── logging_utils.py # Logging utilities
│       │   └── technical_analysis.py # Technical indicators
│       └── gui/
│           ├── main_window.py   # Main GUI window
│           ├── stock_selector.py # Stock selection component
│           └── trading_panel.py # Trading controls and stats
├── tests/
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── requirements/
│   ├── base.txt               # Core dependencies
│   ├── dev.txt                # Development dependencies
│   └── prod.txt               # Production dependencies
├── docs/                      # Documentation
├── .env.example              # Environment template
├── .gitignore               # Git ignore rules
├── pyproject.toml           # Project configuration
└── README.md               # This file
```

## Development

### Setting up Development Environment

1. **Install development dependencies**:
   ```bash
   pip install -r requirements/dev.txt
   ```

2. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

3. **Run tests**:
   ```bash
   pytest
   ```

4. **Code formatting**:
   ```bash
   black src/ tests/
   isort src/ tests/
   ```

5. **Type checking**:
   ```bash
   mypy src/
   ```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/alpaca_bot

# Run specific test file
pytest tests/unit/test_strategy.py
```

### Building

```bash
# Build package
python -m build

# Install in development mode
pip install -e .
```

## API Reference

### Key Classes

- **`AlpacaClient`**: Handles all Alpaca API interactions
- **`ScalpingStrategy`**: Implements the trading strategy logic
- **`MainWindow`**: Primary GUI interface
- **`Settings`**: Configuration management
- **`Trade`**: Trade data model
- **`StockData`**: Market data model

### Configuration Options

| Setting | Description | Default |
|---------|-------------|----------|
| `ALPACA_API_KEY` | Alpaca API key | Required |
| `ALPACA_SECRET_KEY` | Alpaca secret key | Required |
| `ALPACA_BASE_URL` | API base URL | Paper trading URL |
| `TRADING_MODE` | Trading mode | "paper" |
| `MAX_POSITION_SIZE` | Maximum position size | 1000.0 |
| `RISK_PER_TRADE` | Risk percentage per trade | 1.0 |
| `STOP_LOSS_PCT` | Stop loss percentage | 2.0 |
| `TAKE_PROFIT_PCT` | Take profit percentage | 3.0 |

## Logging

The application provides comprehensive logging:

- **Application logs**: `logs/alpaca_bot.log`
- **Trade logs**: `logs/trades.log`
- **Performance logs**: `logs/performance.log`

Log levels can be configured via environment variables.

## Security

- **API Keys**: Stored in environment variables, never in code
- **Paper Trading**: Default mode for safe testing
- **Input Validation**: All user inputs are validated
- **Error Handling**: Graceful handling of API failures

## Troubleshooting

### Common Issues

1. **API Connection Errors**:
   - Verify API keys are correct
   - Check network connectivity
   - Ensure Alpaca account is active

2. **Import Errors**:
   - Verify virtual environment is activated
   - Check all dependencies are installed
   - Ensure Python path is correct

3. **GUI Issues**:
   - Verify tkinter is available
   - Check display settings on headless systems
   - Ensure proper permissions

### Debug Mode

Enable debug logging by setting:
```env
LOG_LEVEL=DEBUG
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for all public functions
- Maintain test coverage above 80%

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

**Important**: This software is for educational and research purposes. Trading stocks involves risk, and you should never trade with money you cannot afford to lose. The authors are not responsible for any financial losses incurred through the use of this software.

Always test thoroughly with paper trading before using real money.

## Support

For support and questions:

1. Check the documentation
2. Review existing issues
3. Create a new issue with detailed information
4. Include logs and error messages

## Roadmap

- [ ] Additional trading strategies
- [ ] Advanced charting capabilities
- [ ] Portfolio optimization
- [ ] Machine learning integration
- [ ] Mobile app companion
- [ ] Cloud deployment options