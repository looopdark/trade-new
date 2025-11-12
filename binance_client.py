"""
Binance Futures API Client
"""
import hmac
import hashlib
import time
import requests
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class BinanceFuturesClient:
    """Binance USDT-M Futures API Client"""
    
    BASE_URL = "https://fapi.binance.com"
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        self.session.headers.update({
            'X-MBX-APIKEY': api_key
        })
    
    def _generate_signature(self, params: Dict) -> str:
        """Generate HMAC SHA256 signature"""
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _request(self, method: str, endpoint: str, signed: bool = False, silent_errors: bool = False, **kwargs) -> Dict:
        """Make API request"""
        url = f"{self.BASE_URL}{endpoint}"
        
        if signed:
            kwargs['timestamp'] = int(time.time() * 1000)
            kwargs['signature'] = self._generate_signature(kwargs)
        
        try:
            if method == "GET":
                response = self.session.get(url, params=kwargs)
            elif method == "POST":
                response = self.session.post(url, params=kwargs)
            elif method == "DELETE":
                response = self.session.delete(url, params=kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if silent_errors:
                logger.debug(f"API request info: {e}")
            else:
                logger.error(f"API request failed: {e}")
            raise
    
    def get_account_balance(self) -> Dict:
        """Get futures account balance"""
        return self._request("GET", "/fapi/v2/balance", signed=True)
    
    def get_account_info(self) -> Dict:
        """Get account information"""
        return self._request("GET", "/fapi/v2/account", signed=True)
    
    def get_klines(self, symbol: str, interval: str, limit: int = 500) -> List:
        """Get candlestick data"""
        return self._request(
            "GET",
            "/fapi/v1/klines",
            symbol=symbol,
            interval=interval,
            limit=limit
        )
    
    def get_ticker_price(self, symbol: str) -> Dict:
        """Get current price"""
        return self._request("GET", "/fapi/v1/ticker/price", symbol=symbol)
    
    def set_leverage(self, symbol: str, leverage: int) -> Dict:
        """Set leverage for symbol"""
        return self._request(
            "POST",
            "/fapi/v1/leverage",
            signed=True,
            symbol=symbol,
            leverage=leverage
        )
    
    def get_position_mode(self) -> Dict:
        """Get current position mode"""
        try:
            return self._request("GET", "/fapi/v1/positionSide/dual", signed=True)
        except Exception as e:
            logger.debug(f"Error getting position mode: {e}")
            return {}
    
    def set_margin_type(self, symbol: str, margin_type: str = "CROSSED") -> Dict:
        """Set margin type (ISOLATED or CROSSED)"""
        try:
            positions = self.get_position_info(symbol)
            if positions:
                current_margin = positions[0].get('marginType', '').upper()
                if current_margin == margin_type:
                    logger.debug(f"{symbol} already using {margin_type} margin")
                    return {"code": 200, "msg": "Margin type already set"}
            
            return self._request(
                "POST",
                "/fapi/v1/marginType",
                signed=True,
                silent_errors=True,
                symbol=symbol,
                marginType=margin_type
            )
        except requests.exceptions.HTTPError as e:
            if "400" in str(e):
                logger.debug(f"{symbol} margin type already set to {margin_type}")
                return {"code": 200, "msg": "Margin type already set"}
            else:
                logger.error(f"Failed to set margin type for {symbol}: {e}")
                raise
        except Exception as e:
            logger.debug(f"Margin type setup for {symbol}: {e}")
            return {"code": 200, "msg": "Using existing margin type"}
    
    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC"
    ) -> Dict:
        """Create a new order"""
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }
        
        if price:
            params["price"] = price
            if order_type == "LIMIT":
                params["timeInForce"] = time_in_force
        
        if stop_price:
            params["stopPrice"] = stop_price
        
        return self._request("POST", "/fapi/v1/order", signed=True, **params)
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """Cancel an order"""
        return self._request(
            "DELETE",
            "/fapi/v1/order",
            signed=True,
            symbol=symbol,
            orderId=order_id
        )
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List:
        """Get all open orders"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", signed=True, **params)
    
    def get_position_info(self, symbol: Optional[str] = None) -> List:
        """Get position information"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v2/positionRisk", signed=True, **params)
    
    def close_position(self, symbol: str, position_side: str, quantity: float) -> Dict:
        """Close a position"""
        side = "SELL" if position_side == "LONG" else "BUY"
        return self.create_order(
            symbol=symbol,
            side=side,
            order_type="MARKET",
            quantity=quantity
        )
    
    def get_exchange_info(self) -> Dict:
        """Get exchange trading rules and symbol information"""
        return self._request("GET", "/fapi/v1/exchangeInfo")
    
    def get_symbol_precision(self, symbol: str) -> Dict:
        """Get price and quantity precision for a symbol"""
        exchange_info = self.get_exchange_info()
        for s in exchange_info['symbols']:
            if s['symbol'] == symbol:
                return {
                    'price_precision': s['pricePrecision'],
                    'quantity_precision': s['quantityPrecision'],
                    'min_qty': float(s['filters'][1]['minQty']),
                    'min_notional': float(s['filters'][5]['notional'])
                }
        return {}
