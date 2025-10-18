"""
Trading Strategy Engine
Manages trading decisions and signal validation
"""
import pandas as pd
from typing import Dict, Optional, List
import logging
from datetime import datetime, timedelta
from indicators import IndicatorAnalyzer
from utils import klines_to_dataframe

logger = logging.getLogger(__name__)


class TradingStrategy:
    """Main trading strategy engine"""
    
    def __init__(self, config: dict):
        self.config = config
        self.analyzer = IndicatorAnalyzer()
        self.signal_history = {}
        self.last_signal_time = {}
        
    def analyze_market(self, symbol: str, klines: List) -> Dict:
        """Analyze market data and generate trading signal"""
        try:
            # Convert klines to dataframe
            df = klines_to_dataframe(klines)
            
            if len(df) < 200:
                logger.warning(f"{symbol}: Not enough data for analysis")
                return self._neutral_signal()
            
            # Calculate all indicators
            indicators = self.analyzer.calculate_all_indicators(df)
            
            if not indicators:
                logger.error(f"{symbol}: Failed to calculate indicators")
                return self._neutral_signal()
            
            # Generate signal
            signal = self.analyzer.generate_signal(df, indicators)
            
            # Add market context
            signal['symbol'] = symbol
            signal['price'] = df['close'].iloc[-1]
            signal['timestamp'] = datetime.now()
            
            # Validate signal
            validated_signal = self._validate_signal(symbol, signal, df, indicators)
            
            # Store signal history
            self._update_signal_history(symbol, validated_signal)
            
            return validated_signal
            
        except Exception as e:
            logger.error(f"{symbol}: Error analyzing market: {e}")
            return self._neutral_signal()
    
    def _validate_signal(self, symbol: str, signal: Dict, df: pd.DataFrame, 
                        indicators: Dict) -> Dict:
        """Validate and filter trading signals"""
        try:
            # Check signal strength threshold
            min_strength = self.config.get('MIN_SIGNAL_STRENGTH', 60)
            if signal['strength'] < min_strength:
                signal['direction'] = 'NEUTRAL'
                signal['valid'] = False
                signal['rejection_reason'] = f"Signal strength too low ({signal['strength']} < {min_strength})"
                return signal
            
            # Check for signal confirmation
            if not self._check_signal_confirmation(symbol, signal):
                signal['direction'] = 'NEUTRAL'
                signal['valid'] = False
                signal['rejection_reason'] = "Insufficient signal confirmation"
                return signal
            
            # Check trend alignment
            if not self._check_trend_alignment(df, indicators, signal['direction']):
                signal['direction'] = 'NEUTRAL'
                signal['valid'] = False
                signal['rejection_reason'] = "Signal against major trend"
                return signal
            
            # Check volatility
            atr = indicators['atr'].iloc[-1]
            price = df['close'].iloc[-1]
            volatility_percent = (atr / price) * 100
            
            if volatility_percent > 5:  # Too volatile
                signal['direction'] = 'NEUTRAL'
                signal['valid'] = False
                signal['rejection_reason'] = f"Volatility too high ({volatility_percent:.2f}%)"
                return signal
            
            # Check time since last signal
            if not self._check_signal_cooldown(symbol):
                signal['direction'] = 'NEUTRAL'
                signal['valid'] = False
                signal['rejection_reason'] = "Signal cooldown period active"
                return signal
            
            # Signal is valid
            signal['valid'] = True
            signal['volatility'] = volatility_percent
            signal['atr'] = atr
            
            # Calculate entry, stop loss, and take profit levels
            signal = self._calculate_trade_levels(signal, df, indicators)
            
            return signal
            
        except Exception as e:
            logger.error(f"{symbol}: Error validating signal: {e}")
            signal['valid'] = False
            signal['rejection_reason'] = f"Validation error: {str(e)}"
            return signal
    
    def _check_signal_confirmation(self, symbol: str, signal: Dict) -> bool:
        """Check if signal has enough confirmations"""
        required_confirmations = self.config.get('SIGNAL_CONFIRMATION_COUNT', 2)
        
        if symbol not in self.signal_history:
            return False
        
        history = self.signal_history[symbol]
        if len(history) < required_confirmations:
            return False
        
        # Check last N signals
        recent_signals = history[-required_confirmations:]
        same_direction = all(s['direction'] == signal['direction'] for s in recent_signals)
        
        return same_direction
    
    def _check_trend_alignment(self, df: pd.DataFrame, indicators: Dict, 
                              direction: str) -> bool:
        """Check if signal aligns with major trend"""
        try:
            # Use EMA 50 and SMA 200 for trend
            ema_50 = indicators['ema_50'].iloc[-1]
            sma_200 = indicators['sma_200'].iloc[-1]
            current_price = df['close'].iloc[-1]
            
            if direction == 'LONG':
                # For long, prefer price above major MAs
                return current_price > ema_50 or (ema_50 > sma_200)
            elif direction == 'SHORT':
                # For short, prefer price below major MAs
                return current_price < ema_50 or (ema_50 < sma_200)
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking trend alignment: {e}")
            return True  # Don't reject on error
    
    def _check_signal_cooldown(self, symbol: str, cooldown_minutes: int = 30) -> bool:
        """Check if enough time has passed since last signal"""
        if symbol not in self.last_signal_time:
            return True
        
        last_time = self.last_signal_time[symbol]
        time_diff = datetime.now() - last_time
        
        return time_diff > timedelta(minutes=cooldown_minutes)
    
    def _calculate_trade_levels(self, signal: Dict, df: pd.DataFrame, 
                                indicators: Dict) -> Dict:
        """Calculate entry, stop loss, and take profit levels"""
        try:
            price = signal['price']
            atr = signal['atr']
            direction = signal['direction']
            
            # Stop loss based on ATR
            stop_loss_percent = self.config.get('STOP_LOSS_PERCENT', 2)
            stop_loss_atr_multiplier = 1.5
            
            if direction == 'LONG':
                # Entry at current price or slightly better
                signal['entry_price'] = price
                
                # Stop loss
                sl_atr = price - (atr * stop_loss_atr_multiplier)
                sl_percent = price * (1 - stop_loss_percent / 100)
                signal['stop_loss'] = max(sl_atr, sl_percent)
                
                # Take profit levels
                signal['take_profits'] = []
                for tp_config in self.config.get('TAKE_PROFIT_LEVELS', []):
                    tp_price = price * (1 + tp_config['percent'] / 100)
                    signal['take_profits'].append({
                        'price': tp_price,
                        'percent': tp_config['percent'],
                        'close_percent': tp_config['close_percent']
                    })
                
            elif direction == 'SHORT':
                # Entry at current price or slightly better
                signal['entry_price'] = price
                
                # Stop loss
                sl_atr = price + (atr * stop_loss_atr_multiplier)
                sl_percent = price * (1 + stop_loss_percent / 100)
                signal['stop_loss'] = min(sl_atr, sl_percent)
                
                # Take profit levels
                signal['take_profits'] = []
                for tp_config in self.config.get('TAKE_PROFIT_LEVELS', []):
                    tp_price = price * (1 - tp_config['percent'] / 100)
                    signal['take_profits'].append({
                        'price': tp_price,
                        'percent': tp_config['percent'],
                        'close_percent': tp_config['close_percent']
                    })
            
            return signal
            
        except Exception as e:
            logger.error(f"Error calculating trade levels: {e}")
            return signal
    
    def _update_signal_history(self, symbol: str, signal: Dict):
        """Update signal history for a symbol"""
        if symbol not in self.signal_history:
            self.signal_history[symbol] = []
        
        self.signal_history[symbol].append({
            'direction': signal['direction'],
            'strength': signal['strength'],
            'timestamp': signal['timestamp'],
            'valid': signal.get('valid', False)
        })
        
        # Keep only last 10 signals
        if len(self.signal_history[symbol]) > 10:
            self.signal_history[symbol] = self.signal_history[symbol][-10:]
        
        # Update last signal time if valid
        if signal.get('valid', False):
            self.last_signal_time[symbol] = signal['timestamp']
    
    def _neutral_signal(self) -> Dict:
        """Return a neutral signal"""
        return {
            'direction': 'NEUTRAL',
            'strength': 0,
            'valid': False,
            'reasons': [],
            'timestamp': datetime.now()
        }
    
    def should_close_position(self, position: Dict, current_price: float, 
                             klines: List) -> Dict:
        """Determine if a position should be closed"""
        try:
            symbol = position['symbol']
            entry_price = position['entry_price']
            side = position['side']
            
            # Calculate current PnL
            if side == 'LONG':
                pnl_percent = ((current_price - entry_price) / entry_price) * 100
            else:  # SHORT
                pnl_percent = ((entry_price - current_price) / entry_price) * 100
            
            # Check stop loss
            if 'stop_loss' in position:
                if side == 'LONG' and current_price <= position['stop_loss']:
                    return {
                        'should_close': True,
                        'reason': 'Stop loss hit',
                        'close_percent': 100,
                        'pnl_percent': pnl_percent
                    }
                elif side == 'SHORT' and current_price >= position['stop_loss']:
                    return {
                        'should_close': True,
                        'reason': 'Stop loss hit',
                        'close_percent': 100,
                        'pnl_percent': pnl_percent
                    }
            
            # Check take profit levels
            if 'take_profits' in position:
                for i, tp in enumerate(position['take_profits']):
                    if tp.get('hit', False):
                        continue
                    
                    if side == 'LONG' and current_price >= tp['price']:
                        return {
                            'should_close': True,
                            'reason': f"Take profit {i+1} hit ({tp['percent']}%)",
                            'close_percent': tp['close_percent'],
                            'pnl_percent': pnl_percent,
                            'tp_index': i
                        }
                    elif side == 'SHORT' and current_price <= tp['price']:
                        return {
                            'should_close': True,
                            'reason': f"Take profit {i+1} hit ({tp['percent']}%)",
                            'close_percent': tp['close_percent'],
                            'pnl_percent': pnl_percent,
                            'tp_index': i
                        }
            
            # Check for reversal signal
            df = klines_to_dataframe(klines)
            indicators = self.analyzer.calculate_all_indicators(df)
            signal = self.analyzer.generate_signal(df, indicators)
            
            if signal['direction'] != 'NEUTRAL' and signal['strength'] > 70:
                if (side == 'LONG' and signal['direction'] == 'SHORT') or \
                   (side == 'SHORT' and signal['direction'] == 'LONG'):
                    return {
                        'should_close': True,
                        'reason': 'Strong reversal signal detected',
                        'close_percent': 100,
                        'pnl_percent': pnl_percent
                    }
            
            return {
                'should_close': False,
                'pnl_percent': pnl_percent
            }
            
        except Exception as e:
            logger.error(f"Error checking position close: {e}")
            return {'should_close': False}
