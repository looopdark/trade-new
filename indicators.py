"""
Technical Indicators Module
Implements all 20 indicators from MQL4 files
"""
import numpy as np
import pandas as pd
from typing import Tuple, List
import logging

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Technical indicators calculator"""
    
    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def smma(data: pd.Series, period: int) -> pd.Series:
        """Smoothed Moving Average"""
        smma = data.copy()
        smma.iloc[:period] = data.iloc[:period].mean()
        for i in range(period, len(data)):
            smma.iloc[i] = (smma.iloc[i-1] * (period - 1) + data.iloc[i]) / period
        return smma
    
    @staticmethod
    def lwma(data: pd.Series, period: int) -> pd.Series:
        """Linear Weighted Moving Average"""
        weights = np.arange(1, period + 1)
        return data.rolling(window=period).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD - Moving Average Convergence Divergence"""
        ema_fast = TechnicalIndicators.ema(data, fast)
        ema_slow = TechnicalIndicators.ema(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                   k_period: int = 14, d_period: int = 3, slowing: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Stochastic Oscillator"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k_fast = 100 * (close - lowest_low) / (highest_high - lowest_low)
        k_slow = k_fast.rolling(window=slowing).mean()
        d_slow = k_slow.rolling(window=d_period).mean()
        
        return k_slow, d_slow
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, deviation: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands"""
        middle = TechnicalIndicators.sma(data, period)
        std = data.rolling(window=period).std()
        upper = middle + (std * deviation)
        lower = middle - (std * deviation)
        return upper, middle, lower
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
    
    @staticmethod
    def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
        """Commodity Channel Index"""
        tp = (high + low + close) / 3
        sma_tp = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        return (tp - sma_tp) / (0.015 * mad)
    
    @staticmethod
    def momentum(data: pd.Series, period: int = 14) -> pd.Series:
        """Momentum Indicator"""
        return data - data.shift(period)
    
    @staticmethod
    def osma(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
        """OsMA - Moving Average of Oscillator"""
        macd_line, signal_line, _ = TechnicalIndicators.macd(data, fast, slow, signal)
        return macd_line - signal_line
    
    @staticmethod
    def parabolic_sar(high: pd.Series, low: pd.Series, acceleration: float = 0.02, 
                      maximum: float = 0.2) -> pd.Series:
        """Parabolic SAR"""
        sar = pd.Series(index=high.index, dtype=float)
        trend = pd.Series(index=high.index, dtype=int)
        ep = pd.Series(index=high.index, dtype=float)
        af = pd.Series(index=high.index, dtype=float)
        
        # Initialize
        sar.iloc[0] = low.iloc[0]
        trend.iloc[0] = 1
        ep.iloc[0] = high.iloc[0]
        af.iloc[0] = acceleration
        
        for i in range(1, len(high)):
            if trend.iloc[i-1] == 1:  # Uptrend
                sar.iloc[i] = sar.iloc[i-1] + af.iloc[i-1] * (ep.iloc[i-1] - sar.iloc[i-1])
                
                if low.iloc[i] < sar.iloc[i]:
                    trend.iloc[i] = -1
                    sar.iloc[i] = ep.iloc[i-1]
                    ep.iloc[i] = low.iloc[i]
                    af.iloc[i] = acceleration
                else:
                    trend.iloc[i] = 1
                    if high.iloc[i] > ep.iloc[i-1]:
                        ep.iloc[i] = high.iloc[i]
                        af.iloc[i] = min(af.iloc[i-1] + acceleration, maximum)
                    else:
                        ep.iloc[i] = ep.iloc[i-1]
                        af.iloc[i] = af.iloc[i-1]
            else:  # Downtrend
                sar.iloc[i] = sar.iloc[i-1] - af.iloc[i-1] * (sar.iloc[i-1] - ep.iloc[i-1])
                
                if high.iloc[i] > sar.iloc[i]:
                    trend.iloc[i] = 1
                    sar.iloc[i] = ep.iloc[i-1]
                    ep.iloc[i] = high.iloc[i]
                    af.iloc[i] = acceleration
                else:
                    trend.iloc[i] = -1
                    if low.iloc[i] < ep.iloc[i-1]:
                        ep.iloc[i] = low.iloc[i]
                        af.iloc[i] = min(af.iloc[i-1] + acceleration, maximum)
                    else:
                        ep.iloc[i] = ep.iloc[i-1]
                        af.iloc[i] = af.iloc[i-1]
        
        return sar
    
    @staticmethod
    def ichimoku(high: pd.Series, low: pd.Series, close: pd.Series,
                 tenkan: int = 9, kijun: int = 26, senkou_b: int = 52) -> dict:
        """Ichimoku Kinko Hyo"""
        # Tenkan-sen (Conversion Line)
        tenkan_sen = (high.rolling(window=tenkan).max() + low.rolling(window=tenkan).min()) / 2
        
        # Kijun-sen (Base Line)
        kijun_sen = (high.rolling(window=kijun).max() + low.rolling(window=kijun).min()) / 2
        
        # Senkou Span A (Leading Span A)
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)
        
        # Senkou Span B (Leading Span B)
        senkou_span_b = ((high.rolling(window=senkou_b).max() + 
                         low.rolling(window=senkou_b).min()) / 2).shift(kijun)
        
        # Chikou Span (Lagging Span)
        chikou_span = close.shift(-kijun)
        
        return {
            'tenkan_sen': tenkan_sen,
            'kijun_sen': kijun_sen,
            'senkou_span_a': senkou_span_a,
            'senkou_span_b': senkou_span_b,
            'chikou_span': chikou_span
        }
    
    @staticmethod
    def zigzag(high: pd.Series, low: pd.Series, depth: int = 12, 
               deviation: int = 5, backstep: int = 3) -> pd.Series:
        """ZigZag Indicator"""
        zigzag = pd.Series(index=high.index, dtype=float)
        last_pivot = 0
        last_pivot_value = 0
        direction = 0
        
        for i in range(depth, len(high)):
            if direction == 0:
                if high.iloc[i] == high.iloc[i-depth:i+1].max():
                    direction = 1
                    last_pivot = i
                    last_pivot_value = high.iloc[i]
                    zigzag.iloc[i] = high.iloc[i]
                elif low.iloc[i] == low.iloc[i-depth:i+1].min():
                    direction = -1
                    last_pivot = i
                    last_pivot_value = low.iloc[i]
                    zigzag.iloc[i] = low.iloc[i]
            elif direction == 1:
                if high.iloc[i] > last_pivot_value:
                    last_pivot = i
                    last_pivot_value = high.iloc[i]
                    zigzag.iloc[i] = high.iloc[i]
                elif low.iloc[i] < last_pivot_value * (1 - deviation/100):
                    direction = -1
                    last_pivot = i
                    last_pivot_value = low.iloc[i]
                    zigzag.iloc[i] = low.iloc[i]
            else:
                if low.iloc[i] < last_pivot_value:
                    last_pivot = i
                    last_pivot_value = low.iloc[i]
                    zigzag.iloc[i] = low.iloc[i]
                elif high.iloc[i] > last_pivot_value * (1 + deviation/100):
                    direction = 1
                    last_pivot = i
                    last_pivot_value = high.iloc[i]
                    zigzag.iloc[i] = high.iloc[i]
        
        return zigzag
    
    @staticmethod
    def alligator(data: pd.Series, jaw: int = 13, teeth: int = 8, 
                  lips: int = 5, jaw_shift: int = 8, teeth_shift: int = 5, 
                  lips_shift: int = 3) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bill Williams' Alligator"""
        jaw_line = TechnicalIndicators.smma(data, jaw).shift(jaw_shift)
        teeth_line = TechnicalIndicators.smma(data, teeth).shift(teeth_shift)
        lips_line = TechnicalIndicators.smma(data, lips).shift(lips_shift)
        return jaw_line, teeth_line, lips_line
    
    @staticmethod
    def awesome_oscillator(high: pd.Series, low: pd.Series) -> pd.Series:
        """Awesome Oscillator"""
        median_price = (high + low) / 2
        ao = TechnicalIndicators.sma(median_price, 5) - TechnicalIndicators.sma(median_price, 34)
        return ao
    
    @staticmethod
    def accelerator_oscillator(high: pd.Series, low: pd.Series) -> pd.Series:
        """Accelerator/Decelerator Oscillator"""
        ao = TechnicalIndicators.awesome_oscillator(high, low)
        ac = ao - TechnicalIndicators.sma(ao, 5)
        return ac
    
    @staticmethod
    def bulls_power(high: pd.Series, close: pd.Series, period: int = 13) -> pd.Series:
        """Bulls Power"""
        ema = TechnicalIndicators.ema(close, period)
        return high - ema
    
    @staticmethod
    def bears_power(low: pd.Series, close: pd.Series, period: int = 13) -> pd.Series:
        """Bears Power"""
        ema = TechnicalIndicators.ema(close, period)
        return low - ema
    
    @staticmethod
    def accumulation_distribution(high: pd.Series, low: pd.Series, 
                                  close: pd.Series, volume: pd.Series) -> pd.Series:
        """Accumulation/Distribution"""
        clv = ((close - low) - (high - close)) / (high - low)
        clv = clv.fillna(0)
        ad = (clv * volume).cumsum()
        return ad
    
    @staticmethod
    def heiken_ashi(open_price: pd.Series, high: pd.Series, 
                    low: pd.Series, close: pd.Series) -> dict:
        """Heiken Ashi Candles"""
        ha_close = (open_price + high + low + close) / 4
        ha_open = pd.Series(index=open_price.index, dtype=float)
        ha_open.iloc[0] = open_price.iloc[0]
        
        for i in range(1, len(open_price)):
            ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2
        
        ha_high = pd.concat([high, ha_open, ha_close], axis=1).max(axis=1)
        ha_low = pd.concat([low, ha_open, ha_close], axis=1).min(axis=1)
        
        return {
            'open': ha_open,
            'high': ha_high,
            'low': ha_low,
            'close': ha_close
        }


class IndicatorAnalyzer:
    """Analyze indicators and generate trading signals"""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> dict:
        """Calculate all indicators for a dataframe"""
        try:
            results = {}
            
            # Price data
            close = df['close']
            high = df['high']
            low = df['low']
            open_price = df['open']
            volume = df['volume']
            
            # Trend Indicators
            results['rsi'] = self.indicators.rsi(close, 14)
            results['macd'], results['macd_signal'], results['macd_hist'] = self.indicators.macd(close)
            results['stoch_k'], results['stoch_d'] = self.indicators.stochastic(high, low, close)
            
            # Volatility Indicators
            results['bb_upper'], results['bb_middle'], results['bb_lower'] = self.indicators.bollinger_bands(close)
            results['atr'] = self.indicators.atr(high, low, close)
            
            # Momentum Indicators
            results['momentum'] = self.indicators.momentum(close)
            results['cci'] = self.indicators.cci(high, low, close)
            results['osma'] = self.indicators.osma(close)
            
            # Moving Averages
            results['ema_9'] = self.indicators.ema(close, 9)
            results['ema_21'] = self.indicators.ema(close, 21)
            results['ema_50'] = self.indicators.ema(close, 50)
            results['sma_200'] = self.indicators.sma(close, 200)
            
            # Advanced Indicators
            results['parabolic_sar'] = self.indicators.parabolic_sar(high, low)
            ichimoku = self.indicators.ichimoku(high, low, close)
            results.update({f'ichimoku_{k}': v for k, v in ichimoku.items()})
            
            results['alligator_jaw'], results['alligator_teeth'], results['alligator_lips'] = \
                self.indicators.alligator(close)
            
            results['awesome_osc'] = self.indicators.awesome_oscillator(high, low)
            results['accelerator_osc'] = self.indicators.accelerator_oscillator(high, low)
            results['bulls_power'] = self.indicators.bulls_power(high, close)
            results['bears_power'] = self.indicators.bears_power(low, close)
            results['ad'] = self.indicators.accumulation_distribution(high, low, close, volume)
            
            # Heiken Ashi
            ha = self.indicators.heiken_ashi(open_price, high, low, close)
            results.update({f'ha_{k}': v for k, v in ha.items()})
            
            return results
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return {}
    
    def generate_signal(self, df: pd.DataFrame, indicators: dict) -> dict:
        """Generate trading signal based on indicators"""
        try:
            signals = {
                'long': 0,
                'short': 0,
                'strength': 0,
                'reasons': []
            }
            
            current_idx = -1
            close_price = df['close'].iloc[current_idx]
            
            # RSI Signals
            rsi = indicators['rsi'].iloc[current_idx]
            if rsi < 30:
                signals['long'] += 15
                signals['reasons'].append(f"RSI oversold ({rsi:.1f})")
            elif rsi > 70:
                signals['short'] += 15
                signals['reasons'].append(f"RSI overbought ({rsi:.1f})")
            
            # MACD Signals
            macd_hist = indicators['macd_hist'].iloc[current_idx]
            macd_hist_prev = indicators['macd_hist'].iloc[current_idx-1]
            if macd_hist > 0 and macd_hist_prev <= 0:
                signals['long'] += 20
                signals['reasons'].append("MACD bullish crossover")
            elif macd_hist < 0 and macd_hist_prev >= 0:
                signals['short'] += 20
                signals['reasons'].append("MACD bearish crossover")
            
            # Stochastic Signals
            stoch_k = indicators['stoch_k'].iloc[current_idx]
            stoch_d = indicators['stoch_d'].iloc[current_idx]
            if stoch_k < 20 and stoch_k > stoch_d:
                signals['long'] += 10
                signals['reasons'].append("Stochastic oversold crossover")
            elif stoch_k > 80 and stoch_k < stoch_d:
                signals['short'] += 10
                signals['reasons'].append("Stochastic overbought crossover")
            
            # Bollinger Bands
            bb_upper = indicators['bb_upper'].iloc[current_idx]
            bb_lower = indicators['bb_lower'].iloc[current_idx]
            if close_price <= bb_lower:
                signals['long'] += 15
                signals['reasons'].append("Price at lower Bollinger Band")
            elif close_price >= bb_upper:
                signals['short'] += 15
                signals['reasons'].append("Price at upper Bollinger Band")
            
            # Moving Average Trend
            ema_9 = indicators['ema_9'].iloc[current_idx]
            ema_21 = indicators['ema_21'].iloc[current_idx]
            ema_50 = indicators['ema_50'].iloc[current_idx]
            
            if ema_9 > ema_21 > ema_50:
                signals['long'] += 15
                signals['reasons'].append("Strong uptrend (EMA alignment)")
            elif ema_9 < ema_21 < ema_50:
                signals['short'] += 15
                signals['reasons'].append("Strong downtrend (EMA alignment)")
            
            # Parabolic SAR
            sar = indicators['parabolic_sar'].iloc[current_idx]
            if close_price > sar:
                signals['long'] += 10
                signals['reasons'].append("Price above SAR")
            else:
                signals['short'] += 10
                signals['reasons'].append("Price below SAR")
            
            # Awesome Oscillator
            ao = indicators['awesome_osc'].iloc[current_idx]
            ao_prev = indicators['awesome_osc'].iloc[current_idx-1]
            if ao > 0 and ao > ao_prev:
                signals['long'] += 5
                signals['reasons'].append("AO bullish")
            elif ao < 0 and ao < ao_prev:
                signals['short'] += 5
                signals['reasons'].append("AO bearish")
            
            # Bulls/Bears Power
            bulls = indicators['bulls_power'].iloc[current_idx]
            bears = indicators['bears_power'].iloc[current_idx]
            if bulls > 0 and bears > bears:
                signals['long'] += 10
                signals['reasons'].append("Bulls power dominant")
            elif bears < 0 and abs(bears) > bulls:
                signals['short'] += 10
                signals['reasons'].append("Bears power dominant")
            
            # Determine final signal
            if signals['long'] > signals['short']:
                signals['direction'] = 'LONG'
                signals['strength'] = signals['long']
            elif signals['short'] > signals['long']:
                signals['direction'] = 'SHORT'
                signals['strength'] = signals['short']
            else:
                signals['direction'] = 'NEUTRAL'
                signals['strength'] = 0
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return {'direction': 'NEUTRAL', 'strength': 0, 'reasons': []}
