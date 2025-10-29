"""
Binance Futures Trading Bot
Main entry point with multi-coin support
"""
import os
import sys
import time
import logging
from datetime import datetime
from typing import Dict, List
import config
from binance_client import BinanceFuturesClient
from strategy import TradingStrategy
from risk_manager import RiskManager
from order_manager import OrderManager
from utils import setup_logger

# Setup logging
logger = setup_logger(__name__, config.LOG_LEVEL)


class BinanceFuturesBot:
    """Main trading bot with multi-coin support"""
    
    def __init__(self):
        logger.info("=" * 60)
        logger.info("Binance Futures Trading Bot Starting...")
        logger.info("=" * 60)
        
        # Initialize components
        self.config = self._load_config()
        self.client = BinanceFuturesClient(
            self.config['BINANCE_API_KEY'],
            self.config['BINANCE_API_SECRET']
        )
        self.risk_manager = RiskManager(self.config, self.client)
        self.order_manager = OrderManager(self.client, self.risk_manager)
        self.strategy = TradingStrategy(self.config)
        
        self.running = False
        self.iteration = 0
        
    def _load_config(self) -> Dict:
        """Load configuration from config.py and environment"""
        cfg = {
            'BINANCE_API_KEY': os.getenv('BINANCE_API_KEY', config.BINANCE_API_KEY),
            'BINANCE_API_SECRET': os.getenv('BINANCE_API_SECRET', config.BINANCE_API_SECRET),
            'TRADING_PAIRS': config.TRADING_PAIRS,
            'LEVERAGE': config.LEVERAGE,
            'MAX_POSITION_SIZE_PERCENT': config.MAX_POSITION_SIZE_PERCENT,
            'MAX_DAILY_LOSS_PERCENT': config.MAX_DAILY_LOSS_PERCENT,
            'MAX_OPEN_POSITIONS': config.MAX_OPEN_POSITIONS,
            'STOP_LOSS_PERCENT': config.STOP_LOSS_PERCENT,
            'DAILY_PROFIT_TARGET': config.DAILY_PROFIT_TARGET,
            'TAKE_PROFIT_LEVELS': config.TAKE_PROFIT_LEVELS,
            'TIMEFRAME': config.TIMEFRAME,
            'CANDLE_LIMIT': config.CANDLE_LIMIT,
            'MIN_SIGNAL_STRENGTH': config.MIN_SIGNAL_STRENGTH,
            'SIGNAL_CONFIRMATION_COUNT': config.SIGNAL_CONFIRMATION_COUNT,
            'UPDATE_INTERVAL': config.UPDATE_INTERVAL,
        }
        
        # Validate API keys
        if not cfg['BINANCE_API_KEY'] or not cfg['BINANCE_API_SECRET']:
            logger.error("API keys not configured!")
            logger.error("Please set BINANCE_API_KEY and BINANCE_API_SECRET in config.py or .env")
            sys.exit(1)
        
        return cfg
    
    def initialize(self):
        """Initialize bot and check connection"""
        try:
            logger.info("Initializing bot...")
            
            # Test API connection
            account_info = self.client.get_account_balance()
            usdt_balance = next(
                (float(b['balance']) for b in account_info if b['asset'] == 'USDT'),
                0
            )
            
            logger.info(f"Connected to Binance Futures")
            logger.info(f"Account Balance: ${usdt_balance:.2f} USDT")
            
            # Initialize risk manager
            self.risk_manager.reset_daily_stats()
            
            # Set leverage for all trading pairs
            for symbol in self.config['TRADING_PAIRS']:
                try:
                    leverage_result = self.client.set_leverage(symbol, self.config['LEVERAGE'])
                    logger.info(f"Set {self.config['LEVERAGE']}x leverage for {symbol}")
                    
                    margin_result = self.client.set_margin_type(symbol, "CROSSED")
                    if margin_result.get('code') == 200:
                        logger.debug(f"{symbol} margin type configured")
                        
                except Exception as e:
                    logger.debug(f"Setup info for {symbol}: {e}")
                    # Continue with next symbol
                    continue
            
            logger.info("Bot initialized successfully")
            logger.info(f"Trading pairs: {', '.join(self.config['TRADING_PAIRS'])}")
            logger.info(f"Timeframe: {self.config['TIMEFRAME']}")
            logger.info(f"Max positions: {self.config['MAX_OPEN_POSITIONS']}")
            logger.info(f"Daily profit target: {self.config['DAILY_PROFIT_TARGET']}%")
            logger.info(f"Max daily loss: {self.config['MAX_DAILY_LOSS_PERCENT']}%")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    def fetch_market_data(self) -> Dict:
        """Fetch market data for all trading pairs"""
        klines_data = {}
        
        for symbol in self.config['TRADING_PAIRS']:
            try:
                klines = self.client.get_klines(
                    symbol,
                    self.config['TIMEFRAME'],
                    self.config['CANDLE_LIMIT']
                )
                klines_data[symbol] = klines
                
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")
        
        return klines_data
    
    def analyze_markets(self, klines_data: Dict) -> Dict:
        """Analyze all markets and generate signals"""
        signals = {}
        
        for symbol, klines in klines_data.items():
            try:
                signal = self.strategy.analyze_market(symbol, klines)
                signals[symbol] = signal
                
                if signal.get('valid', False):
                    logger.info(f"{symbol}: {signal['direction']} signal "
                              f"(strength: {signal['strength']}) - "
                              f"{', '.join(signal['reasons'][:3])}")
                
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
        
        return signals
    
    def execute_signals(self, signals: Dict):
        """Execute valid trading signals"""
        for symbol, signal in signals.items():
            try:
                if not signal.get('valid', False):
                    continue
                
                if signal['direction'] == 'NEUTRAL':
                    continue
                
                # Check if can open position
                can_open = self.risk_manager.can_open_position(symbol)
                if not can_open['allowed']:
                    logger.info(f"{symbol}: Cannot open position - {can_open['reason']}")
                    continue
                
                # Open position
                logger.info(f"{symbol}: Opening {signal['direction']} position...")
                result = self.order_manager.open_position(signal)
                
                if result['success']:
                    logger.info(f"{symbol}: Position opened successfully!")
                    self._log_position_details(result['position'])
                else:
                    logger.warning(f"{symbol}: Failed to open position - {result['reason']}")
                
            except Exception as e:
                logger.error(f"Error executing signal for {symbol}: {e}")
    
    def manage_positions(self, klines_data: Dict):
        """Manage active positions"""
        try:
            # Update positions and check for exits
            actions = self.order_manager.update_positions(klines_data)
            
            for action in actions:
                symbol = action['symbol']
                action_type = action['action']
                details = action['details']
                
                if action_type == 'tp_hit':
                    logger.info(f"{symbol}: TP{details['tp_level']} hit! "
                              f"Closed {details['close_percent']}% | "
                              f"PnL: ${details['pnl']:.2f} ({details['pnl_percent']:.2f}%)")
                
                elif action_type == 'stop_loss':
                    logger.warning(f"{symbol}: Stop loss hit | "
                                 f"PnL: ${details['pnl']:.2f} ({details['pnl_percent']:.2f}%)")
            
        except Exception as e:
            logger.error(f"Error managing positions: {e}")
    
    def _log_position_details(self, position: Dict):
        """Log position details"""
        logger.info(f"  Entry: ${position['entry_price']:.2f}")
        logger.info(f"  Quantity: {position['quantity']:.4f}")
        logger.info(f"  Stop Loss: ${position['stop_loss']:.2f}")
        logger.info(f"  Take Profits:")
        for i, tp in enumerate(position['take_profits']):
            logger.info(f"    TP{i+1}: ${tp['price']:.2f} ({tp['percent']}%) - Close {tp['close_percent']}%")
    
    def print_status(self):
        """Print bot status"""
        try:
            # Get statistics
            stats = self.risk_manager.get_statistics()
            positions = self.order_manager.get_position_summary()
            
            logger.info("=" * 60)
            logger.info(f"Bot Status - Iteration #{self.iteration}")
            logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("-" * 60)
            logger.info(f"Balance: ${stats.get('current_balance', 0):.2f} USDT")
            logger.info(f"Daily PnL: ${stats.get('daily_pnl', 0):.2f} "
                       f"({stats.get('daily_pnl_percent', 0):.2f}%)")
            logger.info(f"Daily Trades: {stats.get('daily_trades', 0)}")
            logger.info(f"Total Trades: {stats.get('total_trades', 0)}")
            logger.info(f"Win Rate: {stats.get('win_rate', 0):.1f}%")
            logger.info(f"Drawdown: {stats.get('drawdown_percent', 0):.2f}%")
            logger.info("-" * 60)
            logger.info(f"Active Positions: {len(positions)}")
            
            if positions:
                for pos in positions:
                    pnl_color = "+" if pos['pnl_percent'] > 0 else ""
                    logger.info(f"  {pos['symbol']}: {pos['side']} | "
                              f"Entry: ${pos['entry_price']:.2f} | "
                              f"Current: ${pos['current_price']:.2f} | "
                              f"PnL: {pnl_color}{pos['pnl_percent']:.2f}% | "
                              f"TP: {pos['tp_hit']}/{pos['tp_levels']}")
            
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error printing status: {e}")
    
    def run(self):
        """Main bot loop"""
        if not self.initialize():
            logger.error("Failed to initialize bot")
            return
        
        self.running = True
        logger.info("Bot is now running. Press Ctrl+C to stop.")
        
        try:
            while self.running:
                self.iteration += 1
                
                try:
                    # Fetch market data
                    klines_data = self.fetch_market_data()
                    
                    if not klines_data:
                        logger.warning("No market data fetched")
                        time.sleep(self.config['UPDATE_INTERVAL'])
                        continue
                    
                    # Manage existing positions
                    self.manage_positions(klines_data)
                    
                    # Analyze markets
                    signals = self.analyze_markets(klines_data)
                    
                    # Execute new signals
                    self.execute_signals(signals)
                    
                    # Print status
                    if self.iteration % 5 == 0:  # Every 5 iterations
                        self.print_status()
                    
                    # Wait before next iteration
                    logger.info(f"Waiting {self.config['UPDATE_INTERVAL']} seconds...")
                    time.sleep(self.config['UPDATE_INTERVAL'])
                    
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    time.sleep(self.config['UPDATE_INTERVAL'])
                    
        except KeyboardInterrupt:
            logger.info("\nShutdown signal received...")
            self.shutdown()
    
    def shutdown(self):
        """Shutdown bot gracefully"""
        logger.info("Shutting down bot...")
        self.running = False
        
        # Print final status
        self.print_status()
        
        # Get active positions
        positions = self.order_manager.get_active_positions()
        if positions:
            logger.warning(f"Warning: {len(positions)} active positions remain open")
            logger.info("Positions will continue to be managed by stop loss and take profit orders")
        
        logger.info("Bot stopped successfully")
        logger.info("=" * 60)


def main():
    """Main entry point"""
    try:
        bot = BinanceFuturesBot()
        bot.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
