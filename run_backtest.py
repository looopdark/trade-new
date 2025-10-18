"""
Run Backtesting Script
Execute backtests and generate reports
"""
import logging
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from backtest import Backtester
from backtest_visualizer import BacktestVisualizer, create_performance_report
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_single_backtest(symbol: str, start_date: str, end_date: str, 
                       initial_balance: float = 10000):
    """Run backtest for a single symbol"""
    try:
        logger.info(f"Starting backtest for {symbol}")
        
        # Create backtester
        backtester = Backtester(initial_balance=initial_balance)
        
        # Run backtest
        results = backtester.run_backtest(symbol, start_date, end_date)
        
        if not results or 'error' in results:
            logger.error(f"Backtest failed: {results.get('error', 'Unknown error')}")
            return None
        
        # Print results
        backtester.print_results(results)
        
        # Create visualizations
        logger.info("Creating visualizations...")
        df = backtester.fetch_historical_data(symbol, start_date, end_date)
        
        visualizer = BacktestVisualizer()
        fig = visualizer.plot_backtest(df, results['trades'], title=f"{symbol} Backtest Results")
        
        if fig:
            filename = f"backtest_{symbol}_{start_date}_{end_date}.png"
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            logger.info(f"Chart saved to {filename}")
            plt.close()
        
        # Create HTML report
        report_filename = f"backtest_report_{symbol}_{start_date}_{end_date}.html"
        create_performance_report(results, report_filename)
        
        return results
        
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        return None


def run_multi_symbol_backtest(symbols: list, start_date: str, end_date: str,
                              initial_balance: float = 10000):
    """Run backtest for multiple symbols"""
    try:
        logger.info(f"Starting multi-symbol backtest for {len(symbols)} symbols")
        
        all_results = {}
        
        for symbol in symbols:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing {symbol}")
            logger.info(f"{'='*60}")
            
            results = run_single_backtest(symbol, start_date, end_date, initial_balance)
            
            if results:
                all_results[symbol] = results
        
        # Print summary
        print("\n" + "="*60)
        print("MULTI-SYMBOL BACKTEST SUMMARY")
        print("="*60)
        
        for symbol, results in all_results.items():
            print(f"\n{symbol}:")
            print(f"  Return: ${results['total_return']:,.2f} ({results['total_return_percent']:.2f}%)")
            print(f"  Win Rate: {results['win_rate']:.2f}%")
            print(f"  Profit Factor: {results['profit_factor']:.2f}")
            print(f"  Max Drawdown: {results['max_drawdown']:.2f}%")
        
        return all_results
        
    except Exception as e:
        logger.error(f"Error running multi-symbol backtest: {e}")
        return {}


if __name__ == "__main__":
    # Configuration
    SYMBOL = "BTCUSDT"
    INITIAL_BALANCE = 10000
    
    # Date range (last 3 months)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    
    print("\n" + "="*60)
    print("BINANCE FUTURES BACKTESTING")
    print("="*60)
    print(f"Symbol: {SYMBOL}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Initial Balance: ${INITIAL_BALANCE:,.2f}")
    print(f"Leverage: {config.LEVERAGE}x")
    print(f"Timeframe: {config.TIMEFRAME}")
    print("="*60 + "\n")
    
    # Run single symbol backtest
    results = run_single_backtest(SYMBOL, start_date, end_date, INITIAL_BALANCE)
    
    # Uncomment to run multi-symbol backtest
    # symbols = config.TRADING_PAIRS
    # results = run_multi_symbol_backtest(symbols, start_date, end_date, INITIAL_BALANCE)
    
    print("\nBacktest completed!")
