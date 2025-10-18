"""
Utility functions for the trading bot
"""
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Dict, List
import pandas as pd
import os


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Setup logger with formatting - logs to both console and file"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    
    if not logger.handlers:
        os.makedirs('logs', exist_ok=True)
        
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        log_filename = f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = RotatingFileHandler(
            log_filename,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"Logging to file: {log_filename}")
    
    return logger


def round_step_size(quantity: float, step_size: float) -> float:
    """Round quantity to exchange step size"""
    precision = len(str(step_size).split('.')[-1].rstrip('0'))
    return round(quantity - (quantity % step_size), precision)


def calculate_position_size(
    balance: float,
    price: float,
    risk_percent: float,
    leverage: int
) -> float:
    """Calculate position size based on risk management"""
    risk_amount = balance * (risk_percent / 100)
    position_value = risk_amount * leverage
    quantity = position_value / price
    return quantity


def klines_to_dataframe(klines: List) -> pd.DataFrame:
    """Convert Binance klines to pandas DataFrame"""
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    return df


def format_number(number: float, decimals: int = 2) -> str:
    """Format number for display"""
    return f"{number:.{decimals}f}"


def calculate_pnl_percent(entry_price: float, current_price: float, side: str) -> float:
    """Calculate PnL percentage"""
    if side == "LONG":
        return ((current_price - entry_price) / entry_price) * 100
    else:  # SHORT
        return ((entry_price - current_price) / entry_price) * 100
