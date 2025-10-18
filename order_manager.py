"""
Order and Multi-TP Manager
Handles order execution and multi take-profit management
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class OrderManager:
    """Manages order execution and multi take-profit levels"""
    
    def __init__(self, client, risk_manager):
        self.client = client
        self.risk_manager = risk_manager
        self.active_positions = {}
        self.pending_orders = {}
        
    def open_position(self, signal: Dict) -> Dict:
        """Open a new position with multi-TP levels"""
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
                return {
                    'success': False,
                    'reason': position_size['reason']
                }
            
            quantity = position_size['quantity']
            
            # Validate trade
            validation = self.risk_manager.validate_trade(
                symbol, direction, quantity, entry_price, stop_loss
            )
            
            if not validation['valid']:
                logger.warning(f"Trade validation failed: {validation['reason']}")
                return {
                    'success': False,
                    'reason': validation['reason']
                }
            
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
                
                # Get actual fill price
                time.sleep(1)  # Wait for order to fill
                positions = self.client.get_position_info(symbol)
                position = next((p for p in positions if float(p['positionAmt']) != 0), None)
                
                if not position:
                    logger.error("Position not found after order execution")
                    return {
                        'success': False,
                        'reason': 'Position not found after execution'
                    }
                
                actual_entry = float(position['entryPrice'])
                actual_quantity = abs(float(position['positionAmt']))
                
                # Place stop loss order
                sl_side = "SELL" if direction == "LONG" else "BUY"
                try:
                    sl_order = self.client.create_order(
                        symbol=symbol,
                        side=sl_side,
                        order_type="STOP_MARKET",
                        quantity=actual_quantity,
                        stop_price=stop_loss
                    )
                    logger.info(f"Stop loss placed at ${stop_loss:.2f}")
                except Exception as e:
                    logger.error(f"Failed to place stop loss: {e}")
                    sl_order = None
                
                # Store position info
                position_info = {
                    'symbol': symbol,
                    'side': direction,
                    'entry_price': actual_entry,
                    'quantity': actual_quantity,
                    'stop_loss': stop_loss,
                    'take_profits': take_profits,
                    'tp_hit': [False] * len(take_profits),
                    'remaining_quantity': actual_quantity,
                    'entry_time': datetime.now(),
                    'order_id': order.get('orderId'),
                    'sl_order_id': sl_order.get('orderId') if sl_order else None,
                    'tp_order_ids': []
                }
                
                self.active_positions[symbol] = position_info
                
                logger.info(f"Position opened successfully: {symbol} {direction} "
                          f"{actual_quantity} @ ${actual_entry:.2f}")
                
                return {
                    'success': True,
                    'position': position_info
                }
                
            except Exception as e:
                logger.error(f"Error placing order: {e}")
                return {
                    'success': False,
                    'reason': f'Order execution failed: {str(e)}'
                }
                
        except Exception as e:
            logger.error(f"Error opening position: {e}")
            return {
                'success': False,
                'reason': f'Error: {str(e)}'
            }
    
    def close_position(self, symbol: str, close_percent: int = 100, 
                      reason: str = "Manual close") -> Dict:
        """Close a position partially or fully"""
        try:
            if symbol not in self.active_positions:
                return {
                    'success': False,
                    'reason': 'Position not found'
                }
            
            position = self.active_positions[symbol]
            remaining_qty = position['remaining_quantity']
            
            if remaining_qty <= 0:
                return {
                    'success': False,
                    'reason': 'No remaining quantity to close'
                }
            
            # Calculate quantity to close
            close_qty = remaining_qty * (close_percent / 100)
            
            # Get symbol precision and round
            precision = self.client.get_symbol_precision(symbol)
            close_qty = round(close_qty, precision['quantity_precision'])
            
            # Place closing order
            side = "SELL" if position['side'] == "LONG" else "BUY"
            
            try:
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    order_type="MARKET",
                    quantity=close_qty
                )
                
                logger.info(f"Closed {close_percent}% of {symbol} position: {close_qty} units")
                
                # Get current price for PnL calculation
                time.sleep(0.5)
                ticker = self.client.get_ticker_price(symbol)
                exit_price = float(ticker['price'])
                
                # Calculate PnL
                if position['side'] == "LONG":
                    pnl = (exit_price - position['entry_price']) * close_qty
                    pnl_percent = ((exit_price - position['entry_price']) / 
                                  position['entry_price']) * 100
                else:
                    pnl = (position['entry_price'] - exit_price) * close_qty
                    pnl_percent = ((position['entry_price'] - exit_price) / 
                                  position['entry_price']) * 100
                
                # Update position
                position['remaining_quantity'] -= close_qty
                
                # If fully closed, remove position and cancel orders
                if close_percent >= 100 or position['remaining_quantity'] <= 0:
                    self._cancel_position_orders(symbol)
                    
                    # Update risk manager
                    position['exit_price'] = exit_price
                    position['pnl'] = pnl
                    position['pnl_percent'] = pnl_percent
                    self.risk_manager.update_position_history(position)
                    
                    del self.active_positions[symbol]
                    logger.info(f"Position fully closed: {symbol} | PnL: ${pnl:.2f} ({pnl_percent:.2f}%)")
                else:
                    logger.info(f"Position partially closed: {symbol} | "
                              f"Remaining: {position['remaining_quantity']:.4f}")
                
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
                return {
                    'success': False,
                    'reason': f'Close order failed: {str(e)}'
                }
                
        except Exception as e:
            logger.error(f"Error in close_position: {e}")
            return {
                'success': False,
                'reason': f'Error: {str(e)}'
            }
    
    def manage_take_profits(self, symbol: str, current_price: float) -> Dict:
        """Manage multi take-profit levels"""
        try:
            if symbol not in self.active_positions:
                return {'action': 'none'}
            
            position = self.active_positions[symbol]
            side = position['side']
            take_profits = position['take_profits']
            
            # Check each TP level
            for i, tp in enumerate(take_profits):
                if position['tp_hit'][i]:
                    continue  # Already hit
                
                tp_price = tp['price']
                tp_percent = tp['close_percent']
                
                # Check if TP level is hit
                tp_hit = False
                if side == "LONG" and current_price >= tp_price:
                    tp_hit = True
                elif side == "SHORT" and current_price <= tp_price:
                    tp_hit = True
                
                if tp_hit:
                    logger.info(f"{symbol}: Take profit {i+1} hit at ${current_price:.2f}")
                    
                    # Close portion of position
                    result = self.close_position(
                        symbol,
                        close_percent=tp_percent,
                        reason=f"Take profit {i+1} ({tp['percent']}%)"
                    )
                    
                    if result['success']:
                        position['tp_hit'][i] = True
                        
                        return {
                            'action': 'tp_hit',
                            'tp_level': i + 1,
                            'close_percent': tp_percent,
                            'pnl': result['pnl'],
                            'pnl_percent': result['pnl_percent']
                        }
            
            return {'action': 'none'}
            
        except Exception as e:
            logger.error(f"Error managing take profits: {e}")
            return {'action': 'error', 'reason': str(e)}
    
    def _cancel_position_orders(self, symbol: str):
        """Cancel all orders for a position"""
        try:
            if symbol not in self.active_positions:
                return
            
            position = self.active_positions[symbol]
            
            # Cancel stop loss
            if position.get('sl_order_id'):
                try:
                    self.client.cancel_order(symbol, position['sl_order_id'])
                    logger.info(f"Cancelled stop loss order for {symbol}")
                except Exception as e:
                    logger.warning(f"Could not cancel SL order: {e}")
            
            # Cancel any TP orders
            for tp_order_id in position.get('tp_order_ids', []):
                try:
                    self.client.cancel_order(symbol, tp_order_id)
                except Exception as e:
                    logger.warning(f"Could not cancel TP order: {e}")
            
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
    
    def update_positions(self, klines_data: Dict) -> List[Dict]:
        """Update all active positions and check for exits"""
        actions = []
        
        try:
            for symbol in list(self.active_positions.keys()):
                if symbol not in klines_data:
                    continue
                
                position = self.active_positions[symbol]
                klines = klines_data[symbol]
                
                # Get current price
                current_price = float(klines[-1][4])  # Close price of last candle
                
                # Check take profit levels
                tp_result = self.manage_take_profits(symbol, current_price)
                if tp_result['action'] == 'tp_hit':
                    actions.append({
                        'symbol': symbol,
                        'action': 'tp_hit',
                        'details': tp_result
                    })
                
                # Check stop loss
                if position['side'] == "LONG" and current_price <= position['stop_loss']:
                    logger.warning(f"{symbol}: Stop loss hit at ${current_price:.2f}")
                    result = self.close_position(symbol, 100, "Stop loss hit")
                    if result['success']:
                        actions.append({
                            'symbol': symbol,
                            'action': 'stop_loss',
                            'details': result
                        })
                
                elif position['side'] == "SHORT" and current_price >= position['stop_loss']:
                    logger.warning(f"{symbol}: Stop loss hit at ${current_price:.2f}")
                    result = self.close_position(symbol, 100, "Stop loss hit")
                    if result['success']:
                        actions.append({
                            'symbol': symbol,
                            'action': 'stop_loss',
                            'details': result
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
                # Get current price
                ticker = self.client.get_ticker_price(symbol)
                current_price = float(ticker['price'])
                
                # Calculate current PnL
                if position['side'] == "LONG":
                    pnl_percent = ((current_price - position['entry_price']) / 
                                  position['entry_price']) * 100
                else:
                    pnl_percent = ((position['entry_price'] - current_price) / 
                                  position['entry_price']) * 100
                
                summary.append({
                    'symbol': symbol,
                    'side': position['side'],
                    'entry_price': position['entry_price'],
                    'current_price': current_price,
                    'quantity': position['remaining_quantity'],
                    'pnl_percent': pnl_percent,
                    'stop_loss': position['stop_loss'],
                    'tp_levels': len(position['take_profits']),
                    'tp_hit': sum(position['tp_hit'])
                })
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting position summary: {e}")
            return summary
