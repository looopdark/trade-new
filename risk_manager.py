"""
Risk Management System
Protects capital and manages position sizing
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from utils import calculate_position_size, round_step_size

logger = logging.getLogger(__name__)


class RiskManager:
    """Manages trading risk and position sizing"""
    
    def __init__(self, config: dict, client):
        self.config = config
        self.client = client
        self.daily_pnl = 0
        self.daily_trades = 0
        self.daily_start_balance = 0
        self.last_reset_date = datetime.now().date()
        self.position_history = []
        self.max_drawdown = 0
        self.peak_balance = 0
        
    def reset_daily_stats(self):
        """Reset daily statistics"""
        try:
            account_info = self.client.get_account_balance()
            usdt_balance = next(
                (float(b['balance']) for b in account_info if b['asset'] == 'USDT'),
                0
            )
            
            self.daily_start_balance = usdt_balance
            self.daily_pnl = 0
            self.daily_trades = 0
            self.last_reset_date = datetime.now().date()
            
            if usdt_balance > self.peak_balance:
                self.peak_balance = usdt_balance
            
            logger.info(f"Daily stats reset. Starting balance: ${usdt_balance:.2f}")
            
        except Exception as e:
            logger.error(f"Error resetting daily stats: {e}")
    
    def check_daily_reset(self):
        """Check if daily stats need to be reset"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.reset_daily_stats()
    
    def can_open_position(self, symbol: str) -> Dict:
        """Check if a new position can be opened"""
        try:
            # Check daily reset
            self.check_daily_reset()
            
            # Get current positions
            positions = self.client.get_position_info()
            open_positions = [p for p in positions if float(p['positionAmt']) != 0]
            
            # Check max open positions
            max_positions = self.config.get('MAX_OPEN_POSITIONS', 5)
            if len(open_positions) >= max_positions:
                return {
                    'allowed': False,
                    'reason': f'Maximum open positions reached ({len(open_positions)}/{max_positions})'
                }
            
            # Check if already have position in this symbol
            existing_position = next(
                (p for p in open_positions if p['symbol'] == symbol),
                None
            )
            if existing_position:
                return {
                    'allowed': False,
                    'reason': f'Already have open position in {symbol}'
                }
            
            # Check daily loss limit
            account_info = self.client.get_account_balance()
            current_balance = next(
                (float(b['balance']) for b in account_info if b['asset'] == 'USDT'),
                0
            )
            
            if self.daily_start_balance > 0:
                daily_pnl_percent = ((current_balance - self.daily_start_balance) / 
                                    self.daily_start_balance) * 100
                
                max_daily_loss = self.config.get('MAX_DAILY_LOSS_PERCENT', 3)
                if daily_pnl_percent <= -max_daily_loss:
                    return {
                        'allowed': False,
                        'reason': f'Daily loss limit reached ({daily_pnl_percent:.2f}% <= -{max_daily_loss}%)'
                    }
                
                # Check daily profit target
                daily_profit_target = self.config.get('DAILY_PROFIT_TARGET', 5)
                if daily_pnl_percent >= daily_profit_target:
                    return {
                        'allowed': False,
                        'reason': f'Daily profit target reached ({daily_pnl_percent:.2f}% >= {daily_profit_target}%)'
                    }
            
            # Check drawdown
            if self.peak_balance > 0:
                drawdown_percent = ((self.peak_balance - current_balance) / 
                                   self.peak_balance) * 100
                
                if drawdown_percent > 10:  # 10% max drawdown
                    return {
                        'allowed': False,
                        'reason': f'Maximum drawdown exceeded ({drawdown_percent:.2f}%)'
                    }
            
            # All checks passed
            return {
                'allowed': True,
                'current_balance': current_balance,
                'open_positions': len(open_positions),
                'daily_pnl_percent': daily_pnl_percent if self.daily_start_balance > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error checking if can open position: {e}")
            return {
                'allowed': False,
                'reason': f'Error: {str(e)}'
            }
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                               stop_loss: float) -> Dict:
        """Calculate optimal position size based on risk management"""
        try:
            # Get account balance
            account_info = self.client.get_account_balance()
            usdt_balance = next(
                (float(b['balance']) for b in account_info if b['asset'] == 'USDT'),
                0
            )
            
            if usdt_balance <= 0:
                return {
                    'success': False,
                    'reason': 'Insufficient balance'
                }
            
            # Get symbol precision
            precision = self.client.get_symbol_precision(symbol)
            if not precision:
                return {
                    'success': False,
                    'reason': 'Could not get symbol precision'
                }
            
            # Calculate risk per trade
            max_position_percent = self.config.get('MAX_POSITION_SIZE_PERCENT', 10)
            leverage = self.config.get('LEVERAGE', 5)
            
            # Calculate position size based on max position percent
            max_position_value = usdt_balance * (max_position_percent / 100) * leverage
            quantity = max_position_value / entry_price
            
            # Calculate risk-based position size
            risk_percent = abs((entry_price - stop_loss) / entry_price) * 100
            if risk_percent > 0:
                # Adjust quantity based on risk
                risk_adjusted_quantity = (usdt_balance * 0.02) / (entry_price * risk_percent / 100)
                quantity = min(quantity, risk_adjusted_quantity)
            
            # Round to symbol precision
            quantity = round_step_size(quantity, precision['min_qty'])
            
            # Check minimum notional
            notional_value = quantity * entry_price
            if notional_value < precision['min_notional']:
                return {
                    'success': False,
                    'reason': f'Position size too small (min notional: ${precision["min_notional"]})'
                }
            
            # Calculate margin required
            margin_required = (quantity * entry_price) / leverage
            
            if margin_required > usdt_balance * 0.9:  # Don't use more than 90% of balance
                return {
                    'success': False,
                    'reason': 'Insufficient margin'
                }
            
            return {
                'success': True,
                'quantity': quantity,
                'notional_value': notional_value,
                'margin_required': margin_required,
                'leverage': leverage,
                'risk_percent': risk_percent,
                'position_percent': (margin_required / usdt_balance) * 100
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {
                'success': False,
                'reason': f'Error: {str(e)}'
            }
    
    def validate_trade(self, symbol: str, side: str, quantity: float, 
                      entry_price: float, stop_loss: float) -> Dict:
        """Validate a trade before execution"""
        try:
            # Check if can open position
            can_open = self.can_open_position(symbol)
            if not can_open['allowed']:
                return {
                    'valid': False,
                    'reason': can_open['reason']
                }
            
            # Validate quantity
            if quantity <= 0:
                return {
                    'valid': False,
                    'reason': 'Invalid quantity'
                }
            
            # Validate prices
            if entry_price <= 0 or stop_loss <= 0:
                return {
                    'valid': False,
                    'reason': 'Invalid price levels'
                }
            
            # Validate stop loss distance
            sl_distance_percent = abs((entry_price - stop_loss) / entry_price) * 100
            if sl_distance_percent > 5:  # Stop loss too far
                return {
                    'valid': False,
                    'reason': f'Stop loss too far ({sl_distance_percent:.2f}%)'
                }
            
            if sl_distance_percent < 0.5:  # Stop loss too close
                return {
                    'valid': False,
                    'reason': f'Stop loss too close ({sl_distance_percent:.2f}%)'
                }
            
            # Calculate potential loss
            potential_loss = quantity * abs(entry_price - stop_loss)
            max_loss_per_trade = can_open['current_balance'] * 0.02  # 2% max loss per trade
            
            if potential_loss > max_loss_per_trade:
                return {
                    'valid': False,
                    'reason': f'Potential loss too high (${potential_loss:.2f} > ${max_loss_per_trade:.2f})'
                }
            
            return {
                'valid': True,
                'potential_loss': potential_loss,
                'risk_reward_ratio': self._calculate_risk_reward(entry_price, stop_loss, side)
            }
            
        except Exception as e:
            logger.error(f"Error validating trade: {e}")
            return {
                'valid': False,
                'reason': f'Validation error: {str(e)}'
            }
    
    def _calculate_risk_reward(self, entry_price: float, stop_loss: float, 
                              side: str, tp_percent: float = 3.0) -> float:
        """Calculate risk/reward ratio"""
        try:
            risk = abs(entry_price - stop_loss)
            
            if side == 'LONG':
                reward = entry_price * (tp_percent / 100)
            else:
                reward = entry_price * (tp_percent / 100)
            
            if risk > 0:
                return reward / risk
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating risk/reward: {e}")
            return 0
    
    def update_position_history(self, position: Dict):
        """Update position history for tracking"""
        self.position_history.append({
            'symbol': position['symbol'],
            'side': position['side'],
            'entry_price': position['entry_price'],
            'exit_price': position.get('exit_price', 0),
            'quantity': position['quantity'],
            'pnl': position.get('pnl', 0),
            'pnl_percent': position.get('pnl_percent', 0),
            'timestamp': datetime.now()
        })
        
        # Keep only last 100 positions
        if len(self.position_history) > 100:
            self.position_history = self.position_history[-100:]
    
    def get_statistics(self) -> Dict:
        """Get risk management statistics"""
        try:
            account_info = self.client.get_account_balance()
            current_balance = next(
                (float(b['balance']) for b in account_info if b['asset'] == 'USDT'),
                0
            )
            
            daily_pnl_percent = 0
            if self.daily_start_balance > 0:
                daily_pnl_percent = ((current_balance - self.daily_start_balance) / 
                                    self.daily_start_balance) * 100
            
            drawdown_percent = 0
            if self.peak_balance > 0:
                drawdown_percent = ((self.peak_balance - current_balance) / 
                                   self.peak_balance) * 100
            
            # Calculate win rate from history
            if self.position_history:
                winning_trades = len([p for p in self.position_history if p['pnl'] > 0])
                total_trades = len(self.position_history)
                win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            else:
                win_rate = 0
            
            return {
                'current_balance': current_balance,
                'daily_start_balance': self.daily_start_balance,
                'daily_pnl': current_balance - self.daily_start_balance,
                'daily_pnl_percent': daily_pnl_percent,
                'daily_trades': self.daily_trades,
                'peak_balance': self.peak_balance,
                'drawdown_percent': drawdown_percent,
                'total_trades': len(self.position_history),
                'win_rate': win_rate
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
