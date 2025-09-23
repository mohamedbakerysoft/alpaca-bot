"""Performance optimization configuration for the Alpaca trading bot.

This module provides centralized performance settings to optimize GUI responsiveness
and reduce system resource usage.
"""

from typing import Dict, Any
import os


class PerformanceConfig:
    """Performance optimization configuration."""
    
    # GUI Update Intervals (in milliseconds)
    TIME_DISPLAY_UPDATE_INTERVAL = 2000  # 2 seconds instead of 1
    ORDER_UPDATE_INTERVAL = 20000        # 20 seconds instead of 15
    POSITION_UPDATE_INTERVAL = 45000     # 45 seconds instead of 30
    MARKET_STATUS_UPDATE_FREQUENCY = 5   # Update every 5 time display updates
    
    # Data Display Settings
    DATA_REFRESH_SKIP_CYCLES = 3         # Refresh data every 3rd cycle
    MIN_DATA_UPDATE_INTERVAL = 3.0       # Minimum 3 seconds between updates
    DATA_UPDATE_MULTIPLIER = 1.5         # Multiply base interval by this factor
    
    # Chart and Graphics Settings
    MAX_CHART_POINTS = 200               # Limit chart data points for performance
    CHART_UPDATE_BATCH_SIZE = 10         # Update charts in batches
    
    # Memory Management
    MAX_PRICE_HISTORY_ITEMS = 1000       # Limit price history storage
    MAX_TRADE_HISTORY_ITEMS = 500        # Limit trade history storage
    
    # Threading Settings
    MAX_WORKER_THREADS = 2               # Limit concurrent threads
    THREAD_JOIN_TIMEOUT = 1.0            # Thread join timeout in seconds
    
    # Lazy Loading Settings
    ENABLE_TAB_LAZY_LOADING = True       # Enable lazy loading for tabs
    PRELOAD_FIRST_TAB_ONLY = True        # Only preload the first tab
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get all performance configuration as a dictionary.
        
        Returns:
            Dictionary containing all performance settings.
        """
        return {
            'gui_updates': {
                'time_display_interval': cls.TIME_DISPLAY_UPDATE_INTERVAL,
                'order_update_interval': cls.ORDER_UPDATE_INTERVAL,
                'position_update_interval': cls.POSITION_UPDATE_INTERVAL,
                'market_status_frequency': cls.MARKET_STATUS_UPDATE_FREQUENCY,
            },
            'data_display': {
                'refresh_skip_cycles': cls.DATA_REFRESH_SKIP_CYCLES,
                'min_update_interval': cls.MIN_DATA_UPDATE_INTERVAL,
                'update_multiplier': cls.DATA_UPDATE_MULTIPLIER,
            },
            'charts': {
                'max_points': cls.MAX_CHART_POINTS,
                'batch_size': cls.CHART_UPDATE_BATCH_SIZE,
            },
            'memory': {
                'max_price_history': cls.MAX_PRICE_HISTORY_ITEMS,
                'max_trade_history': cls.MAX_TRADE_HISTORY_ITEMS,
            },
            'threading': {
                'max_workers': cls.MAX_WORKER_THREADS,
                'join_timeout': cls.THREAD_JOIN_TIMEOUT,
            },
            'lazy_loading': {
                'enable_tab_lazy_loading': cls.ENABLE_TAB_LAZY_LOADING,
                'preload_first_tab_only': cls.PRELOAD_FIRST_TAB_ONLY,
            }
        }
    
    @classmethod
    def apply_env_overrides(cls) -> None:
        """Apply environment variable overrides to performance settings."""
        # Allow environment variables to override default settings
        cls.TIME_DISPLAY_UPDATE_INTERVAL = int(
            os.getenv('PERF_TIME_UPDATE_INTERVAL', cls.TIME_DISPLAY_UPDATE_INTERVAL)
        )
        cls.ORDER_UPDATE_INTERVAL = int(
            os.getenv('PERF_ORDER_UPDATE_INTERVAL', cls.ORDER_UPDATE_INTERVAL)
        )
        cls.POSITION_UPDATE_INTERVAL = int(
            os.getenv('PERF_POSITION_UPDATE_INTERVAL', cls.POSITION_UPDATE_INTERVAL)
        )
        cls.DATA_REFRESH_SKIP_CYCLES = int(
            os.getenv('PERF_DATA_SKIP_CYCLES', cls.DATA_REFRESH_SKIP_CYCLES)
        )
        cls.MAX_CHART_POINTS = int(
            os.getenv('PERF_MAX_CHART_POINTS', cls.MAX_CHART_POINTS)
        )


# Apply environment overrides on import
PerformanceConfig.apply_env_overrides()