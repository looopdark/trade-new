# Binance Futures Trading Bot

Professional automated trading bot for Binance USDT-M Futures with 20 technical indicators, multi-TP system, and advanced risk management.

## Features

- **20 Technical Indicators**: RSI, MACD, Stochastic, Bollinger Bands, Ichimoku, Parabolic SAR, and more
- **Multi Take-Profit System**: Automatically close positions at multiple profit levels
- **Advanced Risk Management**: Daily loss limits, position sizing, drawdown protection
- **Multi-Coin Support**: Trade multiple pairs simultaneously
- **Leverage Trading**: Configurable leverage (default 5x)
- **Stop Loss Protection**: Automatic stop loss on every position
- **Signal Validation**: Multiple confirmation system before opening positions
- **Backtesting System**: Test strategies on historical data before live trading
- **TradingView-style Charts**: Visual analysis with trade markers and performance metrics
- **File Logging**: All activities logged to daily rotating files

## Installation

1. Install Python 3.8 or higher

2. Install dependencies:
\`\`\`bash
pip install -r requirements.txt
\`\`\`

3. Configure API keys:
   - Copy `.env.example` to `.env`
   - Add your Binance API key and secret
   - Or edit `config.py` directly

## Configuration

Edit `config.py` to customize:

- **Trading Pairs**: Add/remove coins to trade
- **Leverage**: Set leverage multiplier (1-125x)
- **Risk Settings**: Max position size, daily loss limit
- **Take Profit Levels**: Customize TP percentages
- **Indicator Parameters**: Fine-tune technical indicators

## Usage

### Live Trading

Run the bot:
\`\`\`bash
python main.py
\`\`\`

The bot will:
1. Connect to Binance Futures
2. Monitor configured trading pairs
3. Analyze markets using 20 indicators
4. Open positions when strong signals detected
5. Manage positions with multi-TP and stop loss
6. Stop trading when daily profit target or loss limit reached

### Backtesting

Test your strategy on historical data:
\`\`\`bash
python run_backtest.py
\`\`\`

The backtesting system will:
1. Fetch historical data from Binance
2. Run strategy on past market conditions
3. Generate performance metrics (win rate, profit factor, Sharpe ratio)
4. Create TradingView-style charts with trade markers
5. Generate HTML performance report

**Backtest Configuration:**
Edit `run_backtest.py` to customize:
- Symbol to test (default: BTCUSDT)
- Date range (default: last 90 days)
- Initial balance (default: $10,000)
- Test multiple symbols simultaneously

**Backtest Outputs:**
- Console: Detailed performance statistics
- PNG Chart: TradingView-style visualization with trades
- HTML Report: Comprehensive performance analysis

**Example Output:**
\`\`\`
BACKTEST RESULTS
============================================================
Account Performance:
  Initial Balance:     $10,000.00
  Final Balance:       $10,450.00
  Total Return:        $450.00 (4.50%)
  Max Drawdown:        2.34%

Trading Statistics:
  Total Trades:        45
  Winning Trades:      28
  Losing Trades:       17
  Win Rate:            62.22%
  Profit Factor:       1.85
\`\`\`

## Risk Management

The bot includes multiple safety features:

- **Position Sizing**: Max 10% of balance per position (configurable)
- **Stop Loss**: 2% stop loss on every trade
- **Daily Loss Limit**: Stops trading at 3% daily loss
- **Daily Profit Target**: Stops trading at 5% daily profit
- **Max Positions**: Limits concurrent positions to 5
- **Drawdown Protection**: Stops trading at 10% drawdown

## Multi Take-Profit System

Default TP levels:
- TP1: 1.5% profit - Close 30% of position
- TP2: 3.0% profit - Close 40% of position
- TP3: 5.0% profit - Close 30% of position

## Technical Indicators Used

1. RSI (Relative Strength Index)
2. MACD (Moving Average Convergence Divergence)
3. Stochastic Oscillator
4. Bollinger Bands
5. ATR (Average True Range)
6. CCI (Commodity Channel Index)
7. Momentum
8. OsMA
9. Parabolic SAR
10. Ichimoku Kinko Hyo
11. Alligator
12. Awesome Oscillator
13. Accelerator Oscillator
14. Bulls Power
15. Bears Power
16. Accumulation/Distribution
17. Heiken Ashi
18. ZigZag
19. Moving Averages (EMA, SMA)
20. Custom Moving Averages

## Strategy

The bot uses a multi-indicator approach:
- Combines signals from all 20 indicators
- Requires minimum signal strength (default 60/100)
- Validates trend alignment
- Checks volatility levels
- Requires signal confirmation
- Only trades in favorable market conditions

## Logging

The bot logs all activities to both console and files:

**Console Output**: Real-time activity display
**Log Files**: Stored in `logs/` directory
- Format: `logs/bot_YYYYMMDD.log` (e.g., `logs/bot_20251016.log`)
- New file created daily automatically
- Maximum file size: 10MB
- Keeps 5 backup files
- All timestamps in local time

**What's Logged:**
- Market analysis results
- Signal generation and strength
- Position opening/closing
- Take profit hits
- Stop loss triggers
- Daily statistics
- API connection status
- Error messages and warnings

**Log Levels:**
- INFO: Normal operations
- WARNING: Important notices (margin type already set, etc.)
- ERROR: Critical issues requiring attention

**Viewing Logs:**
\`\`\`bash
# View today's log
tail -f logs/bot_$(date +%Y%m%d).log

# View last 100 lines
tail -n 100 logs/bot_$(date +%Y%m%d).log

# Search for specific symbol
grep "BTCUSDT" logs/bot_$(date +%Y%m%d).log
\`\`\`

## Safety Notes

1. **Start Small**: Test with small amounts first
2. **Backtest First**: Always backtest your strategy before live trading
3. **Paper Trading**: Consider testing on testnet first
4. **Monitor Regularly**: Check bot performance daily
5. **API Permissions**: Only enable Futures trading permissions
6. **Secure Keys**: Never share your API keys
7. **Understand Risks**: Futures trading involves high risk

## Disclaimer

This bot is for educational purposes. Trading cryptocurrencies involves substantial risk of loss. Use at your own risk. The authors are not responsible for any financial losses.

## Support

For issues or questions:
1. Check configuration in `config.py`
2. Review logs for error messages
3. Ensure API keys have correct permissions
4. Verify sufficient balance in Futures account

## License

MIT License - Use at your own risk
