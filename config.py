"""
Configuration file for Binance Futures Trading Bot
"""

# API Configuration
# API Configuration
BINANCE_API_KEY = "lrRUIpIhs9W2WRo5umApAZIijBRUqE3Fydq2fsDHFfBCmXRkDmaQwu1RmrXW2qqD"  # Your Binance API Key
BINANCE_API_SECRET = "lnxSjdwm226VFA6nTjxcIeXWbRslamVU9jKZqY13GjaQsfp05tELghxwa2YBwbCF"  # Your Binance API Secret

# Trading Configuration
TRADING_PAIRS = [
    "INJUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "ROSEUSDT",
    "XRPUSDT"
]


# Risk Management
MAX_POSITION_SIZE_PERCENT = 10  # Maximum % of balance per position
LEVERAGE = 5  # Leverage multiplier (5x is conservative)
MAX_DAILY_LOSS_PERCENT = 3  # Stop trading if daily loss exceeds this
MAX_OPEN_POSITIONS = 5  # Maximum number of concurrent positions
STOP_LOSS_PERCENT = 1.5  # Stop loss percentage
DAILY_PROFIT_TARGET = 5  # Daily profit target in %

# Multi Take Profit Levels
TAKE_PROFIT_LEVELS = [
    {"percent": 0.8, "close_percent": 100},   # Close 100% at 0.8% profit
]

# "dynamic": Bot monitors price continuously and closes position when TP hit
# "limit": Uses Binance LIMIT orders (price must match exactly)
TP_CONTROL_STRATEGY = {
    "BTCUSDT": "dynamic",      # High value - use dynamic control
    "ETHUSDT": "dynamic",      # High value - use dynamic control
    "BNBUSDT": "limit",        # Can use LIMIT orders
    "SOLUSDT": "limit",        # Can use LIMIT orders
    "ADAUSDT": "dynamic",      # Default - use dynamic control
}

TP_HIT_TOLERANCE = 0.05  # 0.05% tolerance for price matching

AGGRESSIVE_TP_CLOSE = True  # Close immediately when TP hit

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
MIN_SIGNAL_STRENGTH = 40  # Minimum signal strength (0-100) to open position
SIGNAL_CONFIRMATION_COUNT = 0  # Number of confirmations needed (0 = disabled)

# Bot Settings
UPDATE_INTERVAL = 60  # Update interval in seconds
LOG_LEVEL = "INFO"  # Logging level: DEBUG, INFO, WARNING, ERROR
