"""
Order and Multi-TP Manager
Handles order execution and dynamic price monitoring for TP/SL
"""
import logging
from typing import Dict, List
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class OrderManager:
    """Manages order execution and dynamic take-profit/stop-loss monitoring"""
    
    def __init__(self, client, risk_manager):
        self.client = client
        self.risk_manager = risk_manager
        self.active_positions = {}
        
    def open_position(self, signal: Dict) -> Dict:
        """Open a new position without TP/SL orders - bot will monitor dynamically"""
        try:
            symbol = signal['symbol']
            direction = signal['direction']
            entry_price = signal['entry_price']
            stop_loss = signal['stop_loss']
            take_profits = signal['take_profits']
            
            logger.info(f"Opening {direction} position for {symbol} at ${entry_price:.2f}")
            
            # Calculate position size
            position_size = self.risk_manager.calculate_position_size(
                symbol, entry_price, stop_loss
            )
            
            if not position_size['success']:
                logger.warning(f"Cannot calculate position size: {position_size['reason']}")
                return {'success': False, 'reason': position_size['reason']}
            
            quantity = position_size['quantity']
            
            # Validate trade
            validation = self.risk_manager.validate_trade(
                symbol, direction, quantity, entry_price, stop_loss
            )
            
            if not validation['valid']:
                logger.warning(f"Trade validation failed: {validation['reason']}")
                return {'success': False, 'reason': validation['reason']}
            
            # Set leverage
            try:
                leverage = position_size['leverage']
                self.client.set_leverage(symbol, leverage)
                self.client.set_margin_type(symbol, "CROSSED")
                logger.info(f"Set leverage to {leverage}x for {symbol}")
            except Exception as e:
                logger.warning(f"Could not set leverage: {e}")
            
            # Place market order
            side = "BUY" if direction == "LONG" else "SELL"
            
            try:
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    order_type="MARKET",
                    quantity=quantity
                )
                
                logger.info(f"Market order placed: {order}")
                time.sleep(1)  # Wait for order to fill
                
                # Get actual fill price
                positions = self.client.get_position_info(symbol)
                position = next((p for p in positions if float(p['positionAmt']) != 0), None)
                
                if not position:
                    logger.error("Position not found after order execution")
                    return {'success': False, 'reason': 'Position not found after execution'}
                
                actual_entry = float(position['entryPrice'])
                actual_quantity = abs(float(position['positionAmt']))
                precision = self.client.get_symbol_precision(symbol)
                price_precision = precision['price_precision']
                
                processed_tps = []
                for tp in take_profits:
                    tp_price = round(tp['price'], price_precision)
                    processed_tps.append({
                        'price': tp_price,
                        'close_percent': tp['close_percent'],
                        'percent': tp['percent'],
                        'hit': False
                    })
                
                # Store position info
                position_info = {
                    'symbol': symbol,
                    'side': direction,
                    'entry_price': actual_entry,
                    'quantity': actual_quantity,
                    'stop_loss': stop_loss,
                    'take_profits': processed_tps,
                    'remaining_quantity': actual_quantity,
                    'entry_time': datetime.now(),
                    'order_id': order.get('orderId')
                }
                
                self.active_positions[symbol] = position_info
                
                logger.info(f"Position opened successfully: {symbol} {direction} "
                          f"{actual_quantity:.4f} @ ${actual_entry:.8f}")
                
                return {'success': True, 'position': position_info}
                
            except Exception as e:
                logger.error(f"Error placing order: {e}")
                return {'success': False, 'reason': f'Order execution failed: {str(e)}'}
                
        except Exception as e:
            logger.error(f"Error opening position: {e}")
            return {'success': False, 'reason': f'Error: {str(e)}'}
    
    def close_position(self, symbol: str, close_percent: int = 100, 
                      reason: str = "Manual close", price: float = None) -> Dict:
        """Close a position partially or fully"""
        try:
            if symbol not in self.active_positions:
                return {'success': False, 'reason': 'Position not found'}
            
            position = self.active_positions[symbol]
            remaining_qty = position['remaining_quantity']
            
            if remaining_qty <= 0:
                return {'success': False, 'reason': 'No remaining quantity to close'}
            
            # Get symbol precision
            precision = self.client.get_symbol_precision(symbol)
            quantity_precision = precision['quantity_precision']
            min_notional = precision['min_notional']
            
            # Calculate quantity to close
            close_qty = remaining_qty * (close_percent / 100)
            close_qty = round(close_qty, quantity_precision)
            
            if not price:
                ticker = self.client.get_ticker_price(symbol)
                price = float(ticker['price'])
            
            notional_value = close_qty * price
            
            # If notional value too small, use minimum or skip
            if notional_value < min_notional:
                # Round up to meet minimum notional requirement
                close_qty = round(min_notional / price, quantity_precision)
                
                # Make sure we don't exceed remaining quantity
                if close_qty > remaining_qty:
                    close_qty = round(remaining_qty, quantity_precision)
                
                logger.info(f"Adjusted {symbol} close quantity to {close_qty:.8f} to meet minimum notional")
            
            # Place closing market order
            side = "SELL" if position['side'] == "LONG" else "BUY"
            
            try:
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    order_type="MARKET",
                    quantity=close_qty
                )
                
                logger.info(f"Closed {close_percent}% of {symbol}: {close_qty:.8f} units at ${price:.8f}")
                
                # Get exit price
                time.sleep(0.5)
                ticker = self.client.get_ticker_price(symbol)
                exit_price = float(ticker['price']) if not price else price
                
                # Calculate PnL
                if position['side'] == "LONG":
                    pnl = (exit_price - position['entry_price']) * close_qty
                    pnl_percent = ((exit_price - position['entry_price']) / position['entry_price']) * 100
                else:
                    pnl = (position['entry_price'] - exit_price) * close_qty
                    pnl_percent = ((position['entry_price'] - exit_price) / position['entry_price']) * 100
                
                # Update position
                position['remaining_quantity'] -= close_qty
                
                # If fully closed, remove position
                if close_percent >= 100 or position['remaining_quantity'] <= 0:
                    position['exit_price'] = exit_price
                    position['pnl'] = pnl
                    position['pnl_percent'] = pnl_percent
                    self.risk_manager.update_position_history(position)
                    
                    del self.active_positions[symbol]
                    logger.info(f"Position fully closed: {symbol} | PnL: ${pnl:.2f} ({pnl_percent:.2f}%)")
                
                return {
                    'success': True,
                    'closed_quantity': close_qty,
                    'remaining_quantity': position.get('remaining_quantity', 0),
                    'pnl': pnl,
                    'pnl_percent': pnl_percent,
                    'reason': reason
                }
                
            except Exception as e:
                logger.error(f"Error closing position: {e}")
                return {'success': False, 'reason': f'Close order failed: {str(e)}'}
                
        except Exception as e:
            logger.error(f"Error in close_position: {e}")
            return {'success': False, 'reason': f'Error: {str(e)}'}
    
    def _is_small_coin(self, symbol: str) -> bool:
        """Check if coin has small decimals (4+ places after decimal)"""
        try:
            precision = self.client.get_symbol_precision(symbol)
            # If price precision >= 4, it's a small coin
            return precision['price_precision'] >= 4
        except:
            return False
    
    def check_take_profits(self, symbol: str, current_price: float) -> Dict:
        """Check if any take profit levels are hit"""
        try:
            if symbol not in self.active_positions:
                return {'action': 'none'}
            
            position = self.active_positions[symbol]
            side = position['side']
            take_profits = position['take_profits']
            
            for i, tp in enumerate(take_profits):
                if tp['hit']:
                    continue  # Already closed
                
                tp_price = tp['price']
                tp_close_percent = tp['close_percent']
                
                # Check if TP is hit
                tp_hit = False
                if side == "LONG" and current_price >= tp_price:
                    tp_hit = True
                elif side == "SHORT" and current_price <= tp_price:
                    tp_hit = True
                
                if tp_hit:
                    logger.info(f"{symbol}: TP{i+1} ({tp['percent']}%) hit at ${current_price:.8f}")
                    
                    result = self.close_position(
                        symbol,
                        close_percent=tp_close_percent,
                        reason=f"Take profit {i+1} ({tp['percent']}%)",
                        price=current_price
                    )
                    
                    if result['success']:
                        position['take_profits'][i]['hit'] = True
                        return {
                            'action': 'tp_hit',
                            'tp_level': i + 1,
                            'close_percent': tp_close_percent,
                            'pnl': result['pnl'],
                            'pnl_percent': result['pnl_percent']
                        }
            
            return {'action': 'none'}
            
        except Exception as e:
            logger.error(f"Error checking take profits: {e}")
            return {'action': 'error', 'reason': str(e)}
    
    def check_stop_losses(self, symbol: str, current_price: float) -> Dict:
        """Check if stop loss is hit"""
        try:
            if symbol not in self.active_positions:
                return {'action': 'none'}
            
            position = self.active_positions[symbol]
            stop_loss = position['stop_loss']
            side = position['side']
            
            sl_hit = False
            if side == "LONG" and current_price <= stop_loss:
                sl_hit = True
            elif side == "SHORT" and current_price >= stop_loss:
                sl_hit = True
            
            if sl_hit:
                logger.warning(f"{symbol}: Stop loss hit at ${current_price:.8f}")
                
                result = self.close_position(
                    symbol,
                    100,
                    "Stop loss hit",
                    price=current_price
                )
                
                if result['success']:
                    return {
                        'action': 'stop_loss',
                        'pnl': result['pnl'],
                        'pnl_percent': result['pnl_percent']
                    }
            
            return {'action': 'none'}
            
        except Exception as e:
            logger.error(f"Error checking stop loss: {e}")
            return {'action': 'error', 'reason': str(e)}
    
    def update_positions(self, klines_data: Dict) -> List[Dict]:
        """Update all active positions - check TP/SL every candle"""
        actions = []
        
        try:
            for symbol in list(self.active_positions.keys()):
                if symbol not in klines_data:
                    continue
                
                klines = klines_data[symbol]
                current_price = float(klines[-1][4])  # Close price
                
                sl_result = self.check_stop_losses(symbol, current_price)
                if sl_result['action'] == 'stop_loss':
                    actions.append({
                        'symbol': symbol,
                        'action': 'stop_loss',
                        'details': sl_result
                    })
                    continue
                
                # Check TP levels
                tp_result = self.check_take_profits(symbol, current_price)
                if tp_result['action'] == 'tp_hit':
                    actions.append({
                        'symbol': symbol,
                        'action': 'tp_hit',
                        'details': tp_result
                    })
            
            return actions
            
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
            return actions
    
    def get_active_positions(self) -> Dict:
        """Get all active positions"""
        return self.active_positions.copy()
    
    def get_position_summary(self) -> List[Dict]:
        """Get summary of all active positions"""
        summary = []
        
        try:
            for symbol, position in self.active_positions.items():
                ticker = self.client.get_ticker_price(symbol)
                current_price = float(ticker['price'])
                
                # Calculate current PnL
                if position['side'] == "LONG":
                    pnl_percent = ((current_price - position['entry_price']) / position['entry_price']) * 100
                else:
                    pnl_percent = ((position['entry_price'] - current_price) / position['entry_price']) * 100
                
                tp_hit_count = sum(1 for tp in position['take_profits'] if tp['hit'])
                
                summary.append({
                    'symbol': symbol,
                    'side': position['side'],
                    'entry_price': position['entry_price'],
                    'current_price': current_price,
                    'quantity': position['remaining_quantity'],
                    'pnl_percent': pnl_percent,
                    'stop_loss': position['stop_loss'],
                    'tp_levels': len(position['take_profits']),
                    'tp_hit': tp_hit_count
                })
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting position summary: {e}")
            return summary
