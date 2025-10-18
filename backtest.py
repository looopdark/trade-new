"""
Backtesting Engine for Trading Strategy
Tests strategy performance on historical data
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging
from binance_client import BinanceClient
from strategy import TradingStrategy
from utils import klines_to_dataframe
import config

logger = logging.getLogger(__name__)


class Backtester:
    """Backtesting engine for trading strategies"""
    
    def __init__(self, initial_balance: float = 10000, leverage: int = None):
        self.initial_balance = initial_balance
        self.leverage = leverage or config.LEVERAGE
        self.balance = initial_balance
        self.equity = initial_balance
        self.positions = []
        self.closed_trades = []
        self.daily_pnl = {}
        self.peak_balance = initial_balance
        self.max_drawdown = 0
        
        self.strategy = TradingStrategy(config.__dict__)
        self.client = BinanceClient()
        
    def fetch_historical_data(self, symbol: str, start_date: str, end_date: str, 
                             interval: str = None) -> pd.DataFrame:
        """Fetch historical klines data"""
        try:
            interval = interval or config.TIMEFRAME
            logger.info(f"Fetching historical data for {symbol} from {start_date} to {end_date}")
            
            # Convert dates to timestamps
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
            
            all_klines = []
            current_ts = start_ts
            
            while current_ts < end_ts:
                klines = self.client.get_klines(
                    symbol=symbol,
                    interval=interval,
                    start_time=current_ts,
                    limit=1000
                )
                
                if not klines:
                    break
                
                all_klines.extend(klines)
                current_ts = klines[-1][0] + 1
                
                if len(klines) < 1000:
                    break
            
            df = klines_to_dataframe(all_klines)
            logger.info(f"Fetched {len(df)} candles for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()
    
    def run_backtest(self, symbol: str, start_date: str, end_date: str) -> Dict:
        """Run backtest on historical data"""
        try:
            logger.info(f"Starting backtest for {symbol}")
            logger.info(f"Period: {start_date} to {end_date}")
            logger.info(f"Initial Balance: ${self.initial_balance:.2f}")
            logger.info(f"Leverage: {self.leverage}x")
            
            # Fetch historical data
            df = self.fetch_historical_data(symbol, start_date, end_date)
            
            if df.empty:
                logger.error("No historical data available")
                return {}
            
            # Reset state
            self.balance = self.initial_balance
            self.equity = self.initial_balance
            self.positions = []
            self.closed_trades = []
            self.daily_pnl = {}
            self.peak_balance = self.initial_balance
            self.max_drawdown = 0
            
            # Run through each candle
            for i in range(200, len(df)):  # Start after enough data for indicators
                current_candle = df.iloc[i]
                current_time = current_candle['timestamp']
                current_price = current_candle['close']
                
                # Get historical data up to current point
                historical_data = df.iloc[:i+1]
                
                # Update open positions
                self._update_positions(current_price, current_time)
                
                # Check for new signals if we have room for more positions
                if len(self.positions) < config.MAX_OPEN_POSITIONS:
                    # Get last N candles for analysis
                    recent_klines = historical_data.tail(config.CANDLE_LIMIT).values.tolist()
                    
                    # Convert back to kline format for strategy
                    klines_format = []
                    for _, row in historical_data.tail(config.CANDLE_LIMIT).iterrows():
                        klines_format.append([
                            int(row['timestamp'].timestamp() * 1000),
                            str(row['open']),
                            str(row['high']),
                            str(row['low']),
                            str(row['close']),
                            str(row['volume']),
                            0, 0, 0, 0, 0
                        ])
                    
                    # Analyze market
                    signal = self.strategy.analyze_market(symbol, klines_format)
                    
                    # Open position if signal is valid
                    if signal.get('valid', False) and signal['direction'] != 'NEUTRAL':
                        self._open_position(signal, current_price, current_time)
                
                # Track daily PnL
                date_key = current_time.strftime("%Y-%m-%d")
                if date_key not in self.daily_pnl:
                    self.daily_pnl[date_key] = {
                        'start_balance': self.equity,
                        'end_balance': self.equity,
                        'pnl': 0,
                        'pnl_percent': 0
                    }
                
                self.daily_pnl[date_key]['end_balance'] = self.equity
                self.daily_pnl[date_key]['pnl'] = self.equity - self.daily_pnl[date_key]['start_balance']
                self.daily_pnl[date_key]['pnl_percent'] = (
                    self.daily_pnl[date_key]['pnl'] / self.daily_pnl[date_key]['start_balance'] * 100
                )
            
            # Close any remaining positions
            final_price = df.iloc[-1]['close']
            for position in self.positions[:]:
                self._close_position(position, final_price, df.iloc[-1]['timestamp'], "Backtest end")
            
            # Calculate results
            results = self._calculate_results()
            
            return results
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return {}
    
    def _open_position(self, signal: Dict, price: float, timestamp: datetime):
        """Open a new position"""
        try:
            # Calculate position size
            risk_amount = self.balance * (config.MAX_POSITION_SIZE_PERCENT / 100)
            position_size = (risk_amount * self.leverage) / price
            
            position = {
                'symbol': signal['symbol'],
                'side': signal['direction'],
                'entry_price': price,
                'size': position_size,
                'leverage': self.leverage,
                'entry_time': timestamp,
                'stop_loss': signal.get('stop_loss'),
                'take_profits': signal.get('take_profits', []),
                'remaining_size': position_size,
                'realized_pnl': 0
            }
            
            self.positions.append(position)
            logger.info(f"Opened {signal['direction']} position at ${price:.2f}")
            
        except Exception as e:
            logger.error(f"Error opening position: {e}")
    
    def _update_positions(self, current_price: float, current_time: datetime):
        """Update all open positions"""
        for position in self.positions[:]:
            # Calculate current PnL
            if position['side'] == 'LONG':
                pnl = (current_price - position['entry_price']) * position['remaining_size']
            else:  # SHORT
                pnl = (position['entry_price'] - current_price) * position['remaining_size']
            
            # Check stop loss
            if position['stop_loss']:
                if position['side'] == 'LONG' and current_price <= position['stop_loss']:
                    self._close_position(position, current_price, current_time, "Stop loss")
                    continue
                elif position['side'] == 'SHORT' and current_price >= position['stop_loss']:
                    self._close_position(position, current_price, current_time, "Stop loss")
                    continue
            
            # Check take profit levels
            for i, tp in enumerate(position['take_profits']):
                if tp.get('hit', False):
                    continue
                
                hit = False
                if position['side'] == 'LONG' and current_price >= tp['price']:
                    hit = True
                elif position['side'] == 'SHORT' and current_price <= tp['price']:
                    hit = True
                
                if hit:
                    # Close partial position
                    close_size = position['remaining_size'] * (tp['close_percent'] / 100)
                    
                    if position['side'] == 'LONG':
                        partial_pnl = (current_price - position['entry_price']) * close_size
                    else:
                        partial_pnl = (position['entry_price'] - current_price) * close_size
                    
                    position['realized_pnl'] += partial_pnl
                    position['remaining_size'] -= close_size
                    tp['hit'] = True
                    
                    logger.info(f"TP{i+1} hit at ${current_price:.2f}, closed {tp['close_percent']}%, PnL: ${partial_pnl:.2f}")
                    
                    # If all size is closed, remove position
                    if position['remaining_size'] <= 0:
                        self._close_position(position, current_price, current_time, f"All TPs hit")
                        break
            
            # Update equity
            self.equity = self.balance + sum(
                (current_price - p['entry_price']) * p['remaining_size'] if p['side'] == 'LONG'
                else (p['entry_price'] - current_price) * p['remaining_size']
                for p in self.positions
            )
            
            # Update max drawdown
            if self.equity > self.peak_balance:
                self.peak_balance = self.equity
            
            drawdown = (self.peak_balance - self.equity) / self.peak_balance * 100
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
    
    def _close_position(self, position: Dict, price: float, timestamp: datetime, reason: str):
        """Close a position"""
        try:
            # Calculate final PnL
            if position['side'] == 'LONG':
                pnl = (price - position['entry_price']) * position['remaining_size']
            else:
                pnl = (position['entry_price'] - price) * position['remaining_size']
            
            total_pnl = position['realized_pnl'] + pnl
            
            # Update balance
            self.balance += total_pnl
            self.equity = self.balance
            
            # Record trade
            trade = {
                'symbol': position['symbol'],
                'side': position['side'],
                'entry_price': position['entry_price'],
                'exit_price': price,
                'size': position['size'],
                'entry_time': position['entry_time'],
                'exit_time': timestamp,
                'duration': timestamp - position['entry_time'],
                'pnl': total_pnl,
                'pnl_percent': (total_pnl / (position['entry_price'] * position['size'])) * 100,
                'reason': reason
            }
            
            self.closed_trades.append(trade)
            self.positions.remove(position)
            
            logger.info(f"Closed {position['side']} position at ${price:.2f}, PnL: ${total_pnl:.2f} ({reason})")
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
    
    def _calculate_results(self) -> Dict:
        """Calculate backtest results"""
        try:
            if not self.closed_trades:
                return {
                    'error': 'No trades executed',
                    'initial_balance': self.initial_balance,
                    'final_balance': self.balance
                }
            
            # Basic metrics
            total_trades = len(self.closed_trades)
            winning_trades = [t for t in self.closed_trades if t['pnl'] > 0]
            losing_trades = [t for t in self.closed_trades if t['pnl'] <= 0]
            
            win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
            
            total_profit = sum(t['pnl'] for t in winning_trades)
            total_loss = abs(sum(t['pnl'] for t in losing_trades))
            
            profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
            
            avg_win = (total_profit / len(winning_trades)) if winning_trades else 0
            avg_loss = (total_loss / len(losing_trades)) if losing_trades else 0
            
            # Return metrics
            total_return = self.balance - self.initial_balance
            total_return_percent = (total_return / self.initial_balance) * 100
            
            # Daily metrics
            daily_returns = [day['pnl_percent'] for day in self.daily_pnl.values()]
            avg_daily_return = np.mean(daily_returns) if daily_returns else 0
            
            # Sharpe ratio (simplified)
            if daily_returns:
                sharpe_ratio = (np.mean(daily_returns) / np.std(daily_returns)) * np.sqrt(365) if np.std(daily_returns) > 0 else 0
            else:
                sharpe_ratio = 0
            
            results = {
                'initial_balance': self.initial_balance,
                'final_balance': self.balance,
                'total_return': total_return,
                'total_return_percent': total_return_percent,
                'total_trades': total_trades,
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'total_profit': total_profit,
                'total_loss': total_loss,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'max_drawdown': self.max_drawdown,
                'avg_daily_return': avg_daily_return,
                'sharpe_ratio': sharpe_ratio,
                'trades': self.closed_trades,
                'daily_pnl': self.daily_pnl
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error calculating results: {e}")
            return {}
    
    def print_results(self, results: Dict):
        """Print backtest results"""
        if not results or 'error' in results:
            print(f"\nBacktest Error: {results.get('error', 'Unknown error')}")
            return
        
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        
        print(f"\nAccount Performance:")
        print(f"  Initial Balance:     ${results['initial_balance']:,.2f}")
        print(f"  Final Balance:       ${results['final_balance']:,.2f}")
        print(f"  Total Return:        ${results['total_return']:,.2f} ({results['total_return_percent']:.2f}%)")
        print(f"  Max Drawdown:        {results['max_drawdown']:.2f}%")
        
        print(f"\nTrading Statistics:")
        print(f"  Total Trades:        {results['total_trades']}")
        print(f"  Winning Trades:      {results['winning_trades']}")
        print(f"  Losing Trades:       {results['losing_trades']}")
        print(f"  Win Rate:            {results['win_rate']:.2f}%")
        print(f"  Profit Factor:       {results['profit_factor']:.2f}")
        
        print(f"\nProfit/Loss:")
        print(f"  Total Profit:        ${results['total_profit']:,.2f}")
        print(f"  Total Loss:          ${results['total_loss']:,.2f}")
        print(f"  Average Win:         ${results['avg_win']:,.2f}")
        print(f"  Average Loss:        ${results['avg_loss']:,.2f}")
        
        print(f"\nRisk Metrics:")
        print(f"  Avg Daily Return:    {results['avg_daily_return']:.2f}%")
        print(f"  Sharpe Ratio:        {results['sharpe_ratio']:.2f}")
        
        print("\n" + "="*60)
