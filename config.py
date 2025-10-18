"""
Configuration file for Binance Futures Trading Bot
"""

# API Configuration
BINANCE_API_KEY = "lrRUIpIhs9W2WRo5umApAZIijBRUqE3Fydq2fsDHFfBCmXRkDmaQwu1RmrXW2qqD"  # Your Binance API Key
BINANCE_API_SECRET = "lnxSjdwm226VFA6nTjxcIeXWbRslamVU9jKZqY13GjaQsfp05tELghxwa2YBwbCF"  # Your Binance API Secret

# Trading Configuration
TRADING_PAIRS = [
    "BTCUSDT",
    "INJUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "ROSEUSDT"
]

# Risk Management
MAX_POSITION_SIZE_PERCENT = 10  # Maximum % of balance per position
LEVERAGE = 5  # Leverage multiplier (5x is conservative)
MAX_DAILY_LOSS_PERCENT = 3  # Stop trading if daily loss exceeds this
MAX_OPEN_POSITIONS = 5  # Maximum number of concurrent positions
STOP_LOSS_PERCENT = 2  # Stop loss percentage
DAILY_PROFIT_TARGET = 5  # Daily profit target in %

# Multi Take Profit Levels
TAKE_PROFIT_LEVELS = [
    {"percent": 1.5, "close_percent": 30},  # Close 30% at 1.5% profit
    {"percent": 3.0, "close_percent": 40},  # Close 40% at 3% profit
    {"percent": 5.0, "close_percent": 30},  # Close 30% at 5% profit
]

# Technical Indicator Settings
TIMEFRAME = "15m"  # Trading timeframe
CANDLE_LIMIT = 500  # Number of candles to fetch for indicators

# Indicator Parameters
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

STOCHASTIC_K = 14
STOCHASTIC_D = 3
STOCHASTIC_SLOWING = 3

BOLLINGER_PERIOD = 20
BOLLINGER_DEVIATION = 2

ATR_PERIOD = 14

# Strategy Settings
MIN_SIGNAL_STRENGTH = 60  # Minimum signal strength (0-100) to open position
SIGNAL_CONFIRMATION_COUNT = 2  # Number of confirmations needed

# Bot Settings
UPDATE_INTERVAL = 60  # Update interval in seconds
LOG_LEVEL = "INFO"  # Logging level: DEBUG, INFO, WARNING, ERROR
