"""
数据管理模块 - 用于在交易程序和Web界面之间共享数据
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

DATA_FILE = "trading_data.json"
TRADES_FILE = "trades_history.json"

def save_trading_data(data: Dict):
    """保存交易数据"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存交易数据失败: {e}")

def load_trading_data() -> Optional[Dict]:
    """加载交易数据"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"加载交易数据失败: {e}")
        return None

def save_trade_record(trade: Dict):
    """保存交易记录"""
    try:
        # 加载现有记录
        trades = []
        if os.path.exists(TRADES_FILE):
            with open(TRADES_FILE, 'r', encoding='utf-8') as f:
                trades = json.load(f)
        
        # 添加新记录
        trades.append(trade)
        
        # 只保留最近500条记录
        if len(trades) > 500:
            trades = trades[-500:]
        
        # 保存
        with open(TRADES_FILE, 'w', encoding='utf-8') as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存交易记录失败: {e}")

def load_trades_history() -> List[Dict]:
    """加载交易历史"""
    try:
        if os.path.exists(TRADES_FILE):
            with open(TRADES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"加载交易历史失败: {e}")
        return []

def calculate_performance(trades: List[Dict]) -> Dict:
    """计算交易绩效"""
    if not trades:
        return {
            'total_pnl': 0,
            'win_rate': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }
    
    total_pnl = sum(t.get('pnl', 0) for t in trades)
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
    losing_trades = sum(1 for t in trades if t.get('pnl', 0) < 0)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    return {
        'total_pnl': total_pnl,
        'win_rate': win_rate,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades
    }

def update_system_status(
    status: str,
    account_info: Optional[Dict] = None,
    btc_info: Optional[Dict] = None,
    position: Optional[Dict] = None,
    ai_signal: Optional[Dict] = None,
    tp_sl_orders: Optional[Dict] = None
):
    """更新系统状态"""

    # 加载现有数据
    current_data = load_trading_data()
    if current_data is None:
        current_data = {
            "status": "stopped",
            "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "account": {
                "balance": 0,
                "equity": 0,
                "leverage": 0
            },
            "btc": {
                "price": 0,
                "change": 0,
                "timeframe": "15m",
                "mode": "全仓-单向"
            },
            "position": None,
            "performance": {
                "total_pnl": 0,
                "win_rate": 0,
                "total_trades": 0
            },
            "ai_signal": {
                "signal": "HOLD",
                "confidence": "N/A",
                "reason": "等待AI分析...",
                "stop_loss": 0,
                "take_profit": 0,
                "timestamp": "N/A"
            },
            "tp_sl_orders": {
                "stop_loss_order_id": None,
                "take_profit_order_id": None
            }
        }

    # 更新状态
    current_data['status'] = status
    current_data['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if account_info:
        current_data['account'].update(account_info)

    if btc_info:
        current_data['btc'].update(btc_info)

    if position is not None:
        current_data['position'] = position

    if ai_signal:
        current_data['ai_signal'].update(ai_signal)
        current_data['ai_signal']['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if tp_sl_orders is not None:
        current_data['tp_sl_orders'] = tp_sl_orders

    # 计算绩效
    trades = load_trades_history()
    performance = calculate_performance(trades)
    current_data['performance'] = performance

    # 保存
    save_trading_data(current_data)

