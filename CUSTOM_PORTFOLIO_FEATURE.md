# Custom Portfolio Value Feature

## Overview

The Custom Portfolio Value feature allows users to override the real Alpaca account portfolio value for strategy calculations. This is particularly useful for:

- **Strategy Testing**: Test strategies with different portfolio sizes without affecting real account values
- **Risk Management**: Set conservative portfolio values for safer position sizing
- **Simulation**: Simulate trading with larger or smaller portfolios
- **Development**: Test strategy behavior across different portfolio ranges

## Features

### 1. Portfolio Value Override
- Override real Alpaca account portfolio value
- Use custom value for all position sizing calculations
- Maintains real account safety while allowing flexible testing

### 2. Validation & Safety
- **Minimum Value**: $100.00 (prevents extremely small positions)
- **Maximum Value**: $1,000,000.00 (prevents excessive position sizes)
- **Real-time Validation**: Input validation with immediate feedback
- **Error Handling**: Graceful handling of invalid inputs

### 3. Visual Indicators
- **Active Status**: Clear indication when feature is enabled
- **Current Value**: Display of active custom portfolio value
- **Validation Feedback**: Real-time input validation messages

## Configuration

### Settings (settings.py)
```python
# Custom Portfolio Value Feature
custom_portfolio_value_enabled: bool = False  # Enable/disable feature
custom_portfolio_value: float = 10000.0       # Custom portfolio value
min_portfolio_value: float = 100.0            # Minimum allowed value
max_portfolio_value: float = 1000000.0        # Maximum allowed value
```

### Environment Variables
```bash
CUSTOM_PORTFOLIO_VALUE_ENABLED=false
CUSTOM_PORTFOLIO_VALUE=10000.0
MIN_PORTFOLIO_VALUE=100.0
MAX_PORTFOLIO_VALUE=1000000.0
```

## Usage

### GUI Configuration
1. Open the application configuration panel
2. Navigate to the "Position Sizing" section
3. Find the "Custom Portfolio Value" frame
4. Check "Enable Custom Portfolio Value"
5. Enter desired portfolio value (between $100 and $1,000,000)
6. Save settings

### Programmatic Usage
```python
from alpaca_bot.config.settings import Settings

# Enable custom portfolio value
settings = Settings()
settings.custom_portfolio_value_enabled = True
settings.custom_portfolio_value = 50000.0

# The strategy will now use $50,000 for all calculations
```

## How It Works

### Strategy Integration
The feature integrates with the scalping strategy in two key methods:

1. **`refresh_dynamic_parameters()`**: Updates portfolio value for calculations
2. **`_update_trading_mode_parameters()`**: Uses custom value for position sizing

### Portfolio Value Priority
1. **Custom Value** (if enabled): Uses `custom_portfolio_value`
2. **Alpaca Account**: Uses real account portfolio value
3. **Default Fallback**: Uses $10,000 if account value unavailable

### Position Sizing Impact
When enabled, the custom portfolio value affects:
- Maximum position sizes per trading mode
- Risk calculations (stop loss, take profit)
- Portfolio percentage allocations
- Dynamic parameter adjustments

## Trading Mode Examples

With a $50,000 custom portfolio value:

| Trading Mode | Max Position Value | Stop Loss | Take Profit |
|--------------|-------------------|-----------|-------------|
| Ultra Safe   | $12,500 (25%)     | 0.5%      | 1.0%        |
| Conservative | $20,000 (40%)     | 1.0%      | 2.0%        |
| Aggressive   | $30,000 (60%)     | 1.5%      | 3.0%        |

## Compatibility

### Fixed Trade Amount Feature
The Custom Portfolio Value feature works alongside the Fixed Trade Amount feature:
- **Custom Portfolio**: Affects position sizing calculations
- **Fixed Trade Amount**: Limits total trading capital
- **Combined Use**: Both can be enabled simultaneously without conflicts

### Real Account Safety
- Custom portfolio value only affects calculations
- Real account funds remain protected
- Actual trades still limited by real account balance
- No risk of over-leveraging real account

## Validation Rules

### Input Validation
- **Range Check**: Value must be between $100 and $1,000,000
- **Numeric Validation**: Must be a valid positive number
- **Real-time Feedback**: Immediate validation on input change

### Error Handling
- Invalid inputs show error messages
- Out-of-range values are rejected
- Graceful fallback to previous valid value

## Benefits

### For Strategy Development
- Test strategies with different portfolio sizes
- Validate position sizing logic
- Simulate various market conditions
- Safe testing environment

### For Risk Management
- Conservative position sizing
- Controlled exposure testing
- Portfolio size experimentation
- Risk parameter validation

### For Education
- Learn strategy behavior across portfolio sizes
- Understand position sizing impact
- Practice with different capital amounts
- Safe learning environment

## Technical Implementation

### Files Modified
1. **`settings.py`**: Added configuration parameters
2. **`config_panel.py`**: Added GUI controls and validation
3. **`scalping_strategy.py`**: Integrated custom portfolio logic

### Key Methods
- `_validate_custom_portfolio_value()`: Input validation
- `_update_portfolio_value_status()`: Visual status updates
- `refresh_dynamic_parameters()`: Portfolio value integration

## Testing

Run the test script to verify functionality:
```bash
python test_custom_portfolio_feature.py
```

The test validates:
- Default configuration
- Feature activation
- Trading mode calculations
- Compatibility with other features
- Validation ranges

## Troubleshooting

### Common Issues
1. **Invalid Value Error**: Ensure value is between $100 and $1,000,000
2. **Feature Not Active**: Check that the enable checkbox is checked
3. **No Effect on Trades**: Verify settings are saved and strategy restarted

### Debug Steps
1. Check application logs for validation errors
2. Verify settings file contains correct values
3. Restart application after configuration changes
4. Test with the provided test script

## Future Enhancements

Potential improvements:
- Portfolio value presets (small, medium, large)
- Historical portfolio value tracking
- Portfolio growth simulation
- Advanced validation rules
- Integration with backtesting framework