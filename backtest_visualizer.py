"""
TradingView-style Visualization for Backtesting
Creates interactive charts with trade markers
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class BacktestVisualizer:
    """Create TradingView-style visualizations"""
    
    def __init__(self):
        self.fig = None
        self.axes = None
        
    def plot_backtest(self, df: pd.DataFrame, trades: List[Dict], 
                     indicators: Dict = None, title: str = "Backtest Results"):
        """Create comprehensive backtest visualization"""
        try:
            # Create figure with subplots
            fig = plt.figure(figsize=(16, 12))
            
            # Main price chart
            ax1 = plt.subplot(4, 1, 1)
            self._plot_price_chart(ax1, df, trades, title)
            
            # Equity curve
            ax2 = plt.subplot(4, 1, 2)
            self._plot_equity_curve(ax2, trades)
            
            # Drawdown chart
            ax3 = plt.subplot(4, 1, 3)
            self._plot_drawdown(ax3, trades)
            
            # Trade distribution
            ax4 = plt.subplot(4, 1, 4)
            self._plot_trade_distribution(ax4, trades)
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            logger.error(f"Error creating visualization: {e}")
            return None
    
    def _plot_price_chart(self, ax, df: pd.DataFrame, trades: List[Dict], title: str):
        """Plot price chart with trade markers"""
        try:
            # Plot candlesticks (simplified as line for now)
            ax.plot(df['timestamp'], df['close'], label='Close Price', color='#2962FF', linewidth=1)
            
            # Plot moving averages
            if 'ema_9' in df.columns:
                ax.plot(df['timestamp'], df['ema_9'], label='EMA 9', color='#FF6D00', linewidth=1, alpha=0.7)
            if 'ema_21' in df.columns:
                ax.plot(df['timestamp'], df['ema_21'], label='EMA 21', color='#00C853', linewidth=1, alpha=0.7)
            if 'sma_200' in df.columns:
                ax.plot(df['timestamp'], df['sma_200'], label='SMA 200', color='#D500F9', linewidth=1, alpha=0.5)
            
            # Plot trades
            for trade in trades:
                entry_time = trade['entry_time']
                exit_time = trade['exit_time']
                entry_price = trade['entry_price']
                exit_price = trade['exit_price']
                
                # Entry marker
                if trade['side'] == 'LONG':
                    ax.scatter(entry_time, entry_price, color='green', marker='^', s=100, zorder=5, label='Long Entry' if trade == trades[0] else '')
                    ax.scatter(exit_time, exit_price, color='red', marker='v', s=100, zorder=5)
                else:
                    ax.scatter(entry_time, entry_price, color='red', marker='v', s=100, zorder=5, label='Short Entry' if trade == trades[0] else '')
                    ax.scatter(exit_time, exit_price, color='green', marker='^', s=100, zorder=5)
                
                # Draw line connecting entry and exit
                color = 'green' if trade['pnl'] > 0 else 'red'
                ax.plot([entry_time, exit_time], [entry_price, exit_price], 
                       color=color, linestyle='--', alpha=0.3, linewidth=1)
            
            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_ylabel('Price (USDT)', fontsize=10)
            ax.legend(loc='upper left', fontsize=8)
            ax.grid(True, alpha=0.3)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            
        except Exception as e:
            logger.error(f"Error plotting price chart: {e}")
    
    def _plot_equity_curve(self, ax, trades: List[Dict]):
        """Plot equity curve over time"""
        try:
            if not trades:
                return
            
            # Calculate cumulative equity
            equity = [0]
            timestamps = [trades[0]['entry_time']]
            
            for trade in trades:
                equity.append(equity[-1] + trade['pnl'])
                timestamps.append(trade['exit_time'])
            
            ax.plot(timestamps, equity, color='#2962FF', linewidth=2)
            ax.fill_between(timestamps, equity, 0, alpha=0.3, color='#2962FF')
            
            # Add zero line
            ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
            
            ax.set_title('Equity Curve', fontsize=12, fontweight='bold')
            ax.set_ylabel('Cumulative PnL (USDT)', fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            
        except Exception as e:
            logger.error(f"Error plotting equity curve: {e}")
    
    def _plot_drawdown(self, ax, trades: List[Dict]):
        """Plot drawdown chart"""
        try:
            if not trades:
                return
            
            # Calculate drawdown
            equity = [0]
            for trade in trades:
                equity.append(equity[-1] + trade['pnl'])
            
            peak = equity[0]
            drawdowns = []
            timestamps = [trades[0]['entry_time']]
            
            for i, eq in enumerate(equity[1:]):
                if eq > peak:
                    peak = eq
                drawdown = ((peak - eq) / peak * 100) if peak > 0 else 0
                drawdowns.append(-drawdown)
                timestamps.append(trades[i]['exit_time'])
            
            ax.fill_between(timestamps, drawdowns, 0, color='red', alpha=0.3)
            ax.plot(timestamps, drawdowns, color='red', linewidth=2)
            
            ax.set_title('Drawdown', fontsize=12, fontweight='bold')
            ax.set_ylabel('Drawdown (%)', fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            
        except Exception as e:
            logger.error(f"Error plotting drawdown: {e}")
    
    def _plot_trade_distribution(self, ax, trades: List[Dict]):
        """Plot trade PnL distribution"""
        try:
            if not trades:
                return
            
            pnls = [trade['pnl'] for trade in trades]
            colors = ['green' if pnl > 0 else 'red' for pnl in pnls]
            
            bars = ax.bar(range(len(pnls)), pnls, color=colors, alpha=0.6)
            
            # Add zero line
            ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
            
            ax.set_title('Trade Distribution', fontsize=12, fontweight='bold')
            ax.set_xlabel('Trade Number', fontsize=10)
            ax.set_ylabel('PnL (USDT)', fontsize=10)
            ax.grid(True, alpha=0.3, axis='y')
            
        except Exception as e:
            logger.error(f"Error plotting trade distribution: {e}")
    
    def save_chart(self, filename: str = "backtest_results.png"):
        """Save chart to file"""
        try:
            if self.fig:
                self.fig.savefig(filename, dpi=150, bbox_inches='tight')
                logger.info(f"Chart saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving chart: {e}")


def create_performance_report(results: Dict, output_file: str = "backtest_report.html"):
    """Create HTML performance report"""
    try:
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Backtest Performance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #2962FF; border-bottom: 3px solid #2962FF; padding-bottom: 10px; }}
                h2 {{ color: #333; margin-top: 30px; }}
                .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
                .metric-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #2962FF; }}
                .metric-label {{ font-size: 14px; color: #666; margin-bottom: 5px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
                .positive {{ color: #00C853; }}
                .negative {{ color: #D50000; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #2962FF; color: white; }}
                tr:hover {{ background: #f5f5f5; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Backtest Performance Report</h1>
                
                <h2>Account Performance</h2>
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="metric-label">Initial Balance</div>
                        <div class="metric-value">${results['initial_balance']:,.2f}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Final Balance</div>
                        <div class="metric-value">${results['final_balance']:,.2f}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Total Return</div>
                        <div class="metric-value {'positive' if results['total_return'] > 0 else 'negative'}">
                            ${results['total_return']:,.2f} ({results['total_return_percent']:.2f}%)
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Max Drawdown</div>
                        <div class="metric-value negative">{results['max_drawdown']:.2f}%</div>
                    </div>
                </div>
                
                <h2>Trading Statistics</h2>
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="metric-label">Total Trades</div>
                        <div class="metric-value">{results['total_trades']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Win Rate</div>
                        <div class="metric-value {'positive' if results['win_rate'] > 50 else 'negative'}">{results['win_rate']:.2f}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Profit Factor</div>
                        <div class="metric-value {'positive' if results['profit_factor'] > 1 else 'negative'}">{results['profit_factor']:.2f}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Sharpe Ratio</div>
                        <div class="metric-value">{results['sharpe_ratio']:.2f}</div>
                    </div>
                </div>
                
                <h2>Recent Trades</h2>
                <table>
                    <tr>
                        <th>Entry Time</th>
                        <th>Exit Time</th>
                        <th>Side</th>
                        <th>Entry Price</th>
                        <th>Exit Price</th>
                        <th>PnL</th>
                        <th>PnL %</th>
                        <th>Reason</th>
                    </tr>
        """
        
        # Add last 20 trades
        for trade in results['trades'][-20:]:
            pnl_class = 'positive' if trade['pnl'] > 0 else 'negative'
            html += f"""
                    <tr>
                        <td>{trade['entry_time'].strftime('%Y-%m-%d %H:%M')}</td>
                        <td>{trade['exit_time'].strftime('%Y-%m-%d %H:%M')}</td>
                        <td>{trade['side']}</td>
                        <td>${trade['entry_price']:.2f}</td>
                        <td>${trade['exit_price']:.2f}</td>
                        <td class="{pnl_class}">${trade['pnl']:.2f}</td>
                        <td class="{pnl_class}">{trade['pnl_percent']:.2f}%</td>
                        <td>{trade['reason']}</td>
                    </tr>
            """
        
        html += """
                </table>
            </div>
        </body>
        </html>
        """
        
        with open(output_file, 'w') as f:
            f.write(html)
        
        logger.info(f"Performance report saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Error creating performance report: {e}")
