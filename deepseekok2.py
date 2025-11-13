import os
import time
import schedule
from openai import OpenAI
import ccxt
import pandas as pd
import re
from dotenv import load_dotenv
import json
import requests
from datetime import datetime, timedelta
from data_manager import update_system_status, save_trade_record

load_dotenv()

# 初始化DeepSeek客户端
deepseek_client = OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

# 初始化OKX交易所
exchange = ccxt.okx({
    'options': {
        'defaultType': 'swap',  # OKX使用swap表示永续合约
    },
    'apiKey': os.getenv('OKX_API_KEY'),
    'secret': os.getenv('OKX_SECRET'),
    'password': os.getenv('OKX_PASSWORD'),  # OKX需要交易密码
})

# 交易参数配置 - 结合两个版本的优点
TRADE_CONFIG = {
    'symbol': 'BTC/USDT:USDT',  # OKX的合约符号格式
    'leverage': 10,  # 杠杆倍数,只影响保证金不影响下单价值
    'timeframe': '1h',  # 使用1小时K线
    'test_mode': False,  # 测试模式
    'data_points': 168,  # 7天数据（168根1小时K线）
    'analysis_periods': {
        'short_term': 20,  # 短期均线（20小时）
        'medium_term': 50,  # 中期均线（50小时，约2天）
        'long_term': 168  # 长期趋势（168小时，7天）
    },
    # 新增智能仓位参数
    'position_management': {
        'enable_intelligent_position': True,  # 🆕 新增：是否启用智能仓位管理
        'base_usdt_amount': 100,  # USDT投入下单基数
        'high_confidence_multiplier': 1.5,
        'medium_confidence_multiplier': 1.0,
        'low_confidence_multiplier': 0.5,
        'max_position_ratio': 50,  # 单次最大仓位比例
        'trend_strength_multiplier': 1.2
    }
}


def setup_exchange():
    """设置交易所参数 - 强制全仓模式"""
    try:

        # 首先获取合约规格信息
        print("🔍 获取BTC合约规格...")
        markets = exchange.load_markets()
        btc_market = markets[TRADE_CONFIG['symbol']]

        # 获取合约乘数
        contract_size = float(btc_market['contractSize'])
        print(f"✅ 合约规格: 1张 = {contract_size} BTC")

        # 存储合约规格到全局配置
        TRADE_CONFIG['contract_size'] = contract_size
        TRADE_CONFIG['min_amount'] = btc_market['limits']['amount']['min']

        print(f"📏 最小交易量: {TRADE_CONFIG['min_amount']} 张")

        # 先检查现有持仓
        print("🔍 检查现有持仓模式...")
        positions = exchange.fetch_positions([TRADE_CONFIG['symbol']])

        has_isolated_position = False
        isolated_position_info = None

        for pos in positions:
            if pos['symbol'] == TRADE_CONFIG['symbol']:
                contracts = float(pos.get('contracts', 0))
                mode = pos.get('mgnMode')

                if contracts > 0 and mode == 'isolated':
                    has_isolated_position = True
                    isolated_position_info = {
                        'side': pos.get('side'),
                        'size': contracts,
                        'entry_price': pos.get('entryPrice'),
                        'mode': mode
                    }
                    break

        # 2. 如果有逐仓持仓，提示并退出
        if has_isolated_position:
            print("❌ 检测到逐仓持仓，程序无法继续运行！")
            print(f"📊 逐仓持仓详情:")
            print(f"   - 方向: {isolated_position_info['side']}")
            print(f"   - 数量: {isolated_position_info['size']}")
            print(f"   - 入场价: {isolated_position_info['entry_price']}")
            print(f"   - 模式: {isolated_position_info['mode']}")
            print("\n🚨 解决方案:")
            print("1. 手动平掉所有逐仓持仓")
            print("2. 或者将逐仓持仓转为全仓模式")
            print("3. 然后重新启动程序")
            return False

        # 3. 设置单向持仓模式
        print("🔄 设置单向持仓模式...")
        try:
            exchange.set_position_mode(False, TRADE_CONFIG['symbol'])  # False表示单向持仓
            print("✅ 已设置单向持仓模式")
        except Exception as e:
            print(f"⚠️ 设置单向持仓模式失败 (可能已设置): {e}")

        # 4. 设置全仓模式和杠杆
        print("⚙️ 设置全仓模式和杠杆...")
        exchange.set_leverage(
            TRADE_CONFIG['leverage'],
            TRADE_CONFIG['symbol'],
            {'mgnMode': 'cross'}  # 强制全仓模式
        )
        print(f"✅ 已设置全仓模式，杠杆倍数: {TRADE_CONFIG['leverage']}x")

        # 5. 验证设置
        print("🔍 验证账户设置...")
        balance = exchange.fetch_balance()
        usdt_balance = balance['USDT']['free']
        print(f"💰 当前USDT余额: {usdt_balance:.2f}")

        # 获取当前持仓状态
        current_pos = get_current_position()
        if current_pos:
            print(f"📦 当前持仓: {current_pos['side']}仓 {current_pos['size']}张")
        else:
            print("📦 当前无持仓")

        print("🎯 程序配置完成：全仓模式 + 单向持仓")
        return True

    except Exception as e:
        print(f"❌ 交易所设置失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# 全局变量存储历史数据
price_history = []
signal_history = []
position = None

# 全局变量存储止盈止损订单ID
active_tp_sl_orders = {
    'take_profit_order_id': None,
    'stop_loss_order_id': None
}


def calculate_intelligent_position(signal_data, price_data, current_position):
    """计算智能仓位大小 - 修复版"""
    config = TRADE_CONFIG['position_management']

    # 🆕 新增：如果禁用智能仓位，使用固定仓位
    if not config.get('enable_intelligent_position', True):
        fixed_contracts = 0.1  # 固定仓位大小，可以根据需要调整
        print(f"🔧 智能仓位已禁用，使用固定仓位: {fixed_contracts} 张")
        return fixed_contracts

    try:
        # 获取账户余额
        balance = exchange.fetch_balance()
        usdt_balance = balance['USDT']['free']

        # 基础USDT投入
        base_usdt = config['base_usdt_amount']
        print(f"💰 可用USDT余额: {usdt_balance:.2f}, 下单基数{base_usdt}")

        # 根据信心程度调整 - 修复这里
        confidence_multiplier = {
            'HIGH': config['high_confidence_multiplier'],
            'MEDIUM': config['medium_confidence_multiplier'],
            'LOW': config['low_confidence_multiplier']
        }.get(signal_data['confidence'], 1.0)  # 添加默认值

        # 根据趋势强度调整
        trend = price_data['trend_analysis'].get('overall', '震荡整理')
        if trend in ['强势上涨', '强势下跌']:
            trend_multiplier = config['trend_strength_multiplier']
        else:
            trend_multiplier = 1.0

        # 根据RSI状态调整（超买超卖区域减仓）
        rsi = price_data['technical_data'].get('rsi', 50)
        if rsi > 75 or rsi < 25:
            rsi_multiplier = 0.7
        else:
            rsi_multiplier = 1.0

        # 计算建议投入USDT金额
        suggested_usdt = base_usdt * confidence_multiplier * trend_multiplier * rsi_multiplier

        # 风险管理：不超过总资金的指定比例 - 删除重复定义
        max_usdt = usdt_balance * config['max_position_ratio']
        final_usdt = min(suggested_usdt, max_usdt)

        # 正确的合约张数计算！
        # 公式：合约张数 = (投入USDT) / (当前价格 * 合约乘数)
        contract_size = (final_usdt) / (price_data['price'] * TRADE_CONFIG['contract_size'])

        print(f"📊 仓位计算详情:")
        print(f"   - 基础USDT: {base_usdt}")
        print(f"   - 信心倍数: {confidence_multiplier}")
        print(f"   - 趋势倍数: {trend_multiplier}")
        print(f"   - RSI倍数: {rsi_multiplier}")
        print(f"   - 建议USDT: {suggested_usdt:.2f}")
        print(f"   - 最终USDT: {final_usdt:.2f}")
        print(f"   - 合约乘数: {TRADE_CONFIG['contract_size']}")
        print(f"   - 计算合约: {contract_size:.4f} 张")

        # 精度处理：OKX BTC合约最小交易单位为0.01张
        contract_size = round(contract_size, 2)  # 保留2位小数

        # 确保最小交易量
        min_contracts = TRADE_CONFIG.get('min_amount', 0.01)
        if contract_size < min_contracts:
            contract_size = min_contracts
            print(f"⚠️ 仓位小于最小值，调整为: {contract_size} 张")

        print(f"🎯 最终仓位: {final_usdt:.2f} USDT → {contract_size:.2f} 张合约")
        return contract_size

    except Exception as e:
        print(f"❌ 仓位计算失败，使用基础仓位: {e}")
        # 紧急备用计算
        base_usdt = config['base_usdt_amount']
        contract_size = (base_usdt * TRADE_CONFIG['leverage']) / (
                    price_data['price'] * TRADE_CONFIG.get('contract_size', 0.01))
        return round(max(contract_size, TRADE_CONFIG.get('min_amount', 0.01)), 2)


def calculate_technical_indicators(df):
    """计算技术指标 - 来自第一个策略"""
    try:
        # 移动平均线
        df['sma_5'] = df['close'].rolling(window=5, min_periods=1).mean()
        df['sma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
        df['sma_50'] = df['close'].rolling(window=50, min_periods=1).mean()

        # 指数移动平均线
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']

        # 相对强弱指数 (RSI)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # 布林带
        df['bb_middle'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        # 成交量均线
        df['volume_ma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        # 支撑阻力位
        df['resistance'] = df['high'].rolling(20).max()
        df['support'] = df['low'].rolling(20).min()

        # 填充NaN值
        df = df.bfill().ffill()

        return df
    except Exception as e:
        print(f"技术指标计算失败: {e}")
        return df


def get_support_resistance_levels(df, lookback=20):
    """计算支撑阻力位"""
    try:
        recent_high = df['high'].tail(lookback).max()
        recent_low = df['low'].tail(lookback).min()
        current_price = df['close'].iloc[-1]

        resistance_level = recent_high
        support_level = recent_low

        # 动态支撑阻力（基于布林带）
        bb_upper = df['bb_upper'].iloc[-1]
        bb_lower = df['bb_lower'].iloc[-1]

        return {
            'static_resistance': resistance_level,
            'static_support': support_level,
            'dynamic_resistance': bb_upper,
            'dynamic_support': bb_lower,
            'price_vs_resistance': ((resistance_level - current_price) / current_price) * 100,
            'price_vs_support': ((current_price - support_level) / support_level) * 100
        }
    except Exception as e:
        print(f"支撑阻力计算失败: {e}")
        return {}


def get_sentiment_indicators():
    """获取情绪指标 - 简洁版本"""
    try:
        API_URL = "https://service.cryptoracle.network/openapi/v2/endpoint"
        API_KEY = "7ad48a56-8730-4238-a714-eebc30834e3e"

        # 获取最近4小时数据
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=4)

        request_body = {
            "apiKey": API_KEY,
            "endpoints": ["CO-A-02-01", "CO-A-02-02"],  # 只保留核心指标
            "startTime": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "timeType": "15m",
            "token": ["BTC"]
        }

        headers = {"Content-Type": "application/json", "X-API-KEY": API_KEY}
        response = requests.post(API_URL, json=request_body, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200 and data.get("data"):
                time_periods = data["data"][0]["timePeriods"]

                # 查找第一个有有效数据的时间段
                for period in time_periods:
                    period_data = period.get("data", [])

                    sentiment = {}
                    valid_data_found = False

                    for item in period_data:
                        endpoint = item.get("endpoint")
                        value = item.get("value", "").strip()

                        if value:  # 只处理非空值
                            try:
                                if endpoint in ["CO-A-02-01", "CO-A-02-02"]:
                                    sentiment[endpoint] = float(value)
                                    valid_data_found = True
                            except (ValueError, TypeError):
                                continue

                    # 如果找到有效数据
                    if valid_data_found and "CO-A-02-01" in sentiment and "CO-A-02-02" in sentiment:
                        positive = sentiment['CO-A-02-01']
                        negative = sentiment['CO-A-02-02']
                        net_sentiment = positive - negative

                        # 正确的时间延迟计算
                        data_delay = int((datetime.now() - datetime.strptime(
                            period['startTime'], '%Y-%m-%d %H:%M:%S')).total_seconds() // 60)

                        print(f"✅ 使用情绪数据时间: {period['startTime']} (延迟: {data_delay}分钟)")

                        return {
                            'positive_ratio': positive,
                            'negative_ratio': negative,
                            'net_sentiment': net_sentiment,
                            'data_time': period['startTime'],
                            'data_delay_minutes': data_delay
                        }

                print("❌ 所有时间段数据都为空")
                return None

        return None
    except Exception as e:
        print(f"情绪指标获取失败: {e}")
        return None


def get_market_trend(df):
    """判断市场趋势"""
    try:
        current_price = df['close'].iloc[-1]

        # 多时间框架趋势分析
        trend_short = "上涨" if current_price > df['sma_20'].iloc[-1] else "下跌"
        trend_medium = "上涨" if current_price > df['sma_50'].iloc[-1] else "下跌"

        # MACD趋势
        macd_trend = "bullish" if df['macd'].iloc[-1] > df['macd_signal'].iloc[-1] else "bearish"

        # 综合趋势判断
        if trend_short == "上涨" and trend_medium == "上涨":
            overall_trend = "强势上涨"
        elif trend_short == "下跌" and trend_medium == "下跌":
            overall_trend = "强势下跌"
        else:
            overall_trend = "震荡整理"

        return {
            'short_term': trend_short,
            'medium_term': trend_medium,
            'macd': macd_trend,
            'overall': overall_trend,
            'rsi_level': df['rsi'].iloc[-1]
        }
    except Exception as e:
        print(f"趋势分析失败: {e}")
        return {}


def get_btc_ohlcv_enhanced():
    """增强版：获取BTC K线数据并计算技术指标"""
    try:
        # 获取K线数据
        ohlcv = exchange.fetch_ohlcv(TRADE_CONFIG['symbol'], TRADE_CONFIG['timeframe'],
                                     limit=TRADE_CONFIG['data_points'])

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # 计算技术指标
        df = calculate_technical_indicators(df)

        current_data = df.iloc[-1]
        previous_data = df.iloc[-2]

        # 获取技术分析数据
        trend_analysis = get_market_trend(df)
        levels_analysis = get_support_resistance_levels(df)

        return {
            'price': current_data['close'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'high': current_data['high'],
            'low': current_data['low'],
            'volume': current_data['volume'],
            'timeframe': TRADE_CONFIG['timeframe'],
            'price_change': ((current_data['close'] - previous_data['close']) / previous_data['close']) * 100,
            'kline_data': df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].tail(10).to_dict('records'),
            'technical_data': {
                'sma_5': current_data.get('sma_5', 0),
                'sma_20': current_data.get('sma_20', 0),
                'sma_50': current_data.get('sma_50', 0),
                'rsi': current_data.get('rsi', 0),
                'macd': current_data.get('macd', 0),
                'macd_signal': current_data.get('macd_signal', 0),
                'macd_histogram': current_data.get('macd_histogram', 0),
                'bb_upper': current_data.get('bb_upper', 0),
                'bb_lower': current_data.get('bb_lower', 0),
                'bb_position': current_data.get('bb_position', 0),
                'volume_ratio': current_data.get('volume_ratio', 0)
            },
            'trend_analysis': trend_analysis,
            'levels_analysis': levels_analysis,
            'full_data': df
        }
    except Exception as e:
        print(f"获取增强K线数据失败: {e}")
        return None


def generate_technical_analysis_text(price_data):
    """生成技术分析文本"""
    if 'technical_data' not in price_data:
        return "技术指标数据不可用"

    tech = price_data['technical_data']
    trend = price_data.get('trend_analysis', {})
    levels = price_data.get('levels_analysis', {})

    # 检查数据有效性
    def safe_float(value, default=0):
        return float(value) if value and pd.notna(value) else default

    analysis_text = f"""
    【技术指标分析】
    📈 移动平均线:
    - 5周期: {safe_float(tech['sma_5']):.2f} | 价格相对: {(price_data['price'] - safe_float(tech['sma_5'])) / safe_float(tech['sma_5']) * 100:+.2f}%
    - 20周期: {safe_float(tech['sma_20']):.2f} | 价格相对: {(price_data['price'] - safe_float(tech['sma_20'])) / safe_float(tech['sma_20']) * 100:+.2f}%
    - 50周期: {safe_float(tech['sma_50']):.2f} | 价格相对: {(price_data['price'] - safe_float(tech['sma_50'])) / safe_float(tech['sma_50']) * 100:+.2f}%

    🎯 趋势分析:
    - 短期趋势: {trend.get('short_term', 'N/A')}
    - 中期趋势: {trend.get('medium_term', 'N/A')}
    - 整体趋势: {trend.get('overall', 'N/A')}
    - MACD方向: {trend.get('macd', 'N/A')}

    📊 动量指标:
    - RSI: {safe_float(tech['rsi']):.2f} ({'超买' if safe_float(tech['rsi']) > 70 else '超卖' if safe_float(tech['rsi']) < 30 else '中性'})
    - MACD: {safe_float(tech['macd']):.4f}
    - 信号线: {safe_float(tech['macd_signal']):.4f}

    🎚️ 布林带位置: {safe_float(tech['bb_position']):.2%} ({'上部' if safe_float(tech['bb_position']) > 0.7 else '下部' if safe_float(tech['bb_position']) < 0.3 else '中部'})

    💰 关键水平:
    - 静态阻力: {safe_float(levels.get('static_resistance', 0)):.2f}
    - 静态支撑: {safe_float(levels.get('static_support', 0)):.2f}
    """
    return analysis_text


def get_current_position():
    """获取当前持仓情况 - OKX版本"""
    try:
        positions = exchange.fetch_positions([TRADE_CONFIG['symbol']])

        for pos in positions:
            if pos['symbol'] == TRADE_CONFIG['symbol']:
                contracts = float(pos['contracts']) if pos['contracts'] else 0

                if contracts > 0:
                    return {
                        'side': pos['side'],  # 'long' or 'short'
                        'size': contracts,
                        'entry_price': float(pos['entryPrice']) if pos['entryPrice'] else 0,
                        'unrealized_pnl': float(pos['unrealizedPnl']) if pos['unrealizedPnl'] else 0,
                        'leverage': float(pos['leverage']) if pos['leverage'] else TRADE_CONFIG['leverage'],
                        'symbol': pos['symbol']
                    }

        return None

    except Exception as e:
        print(f"获取持仓失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def safe_json_parse(json_str):
    """安全解析JSON，处理格式不规范的情况"""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            # 修复常见的JSON格式问题
            json_str = json_str.replace("'", '"')
            json_str = re.sub(r'(\w+):', r'"\1":', json_str)
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON解析失败，原始内容: {json_str}")
            print(f"错误详情: {e}")
            return None


def create_fallback_signal(price_data):
    """创建备用交易信号"""
    return {
        "signal": "HOLD",
        "reason": "因技术分析暂时不可用，采取保守策略",
        "stop_loss": price_data['price'] * 0.98,  # -2%
        "take_profit": price_data['price'] * 1.02,  # +2%
        "confidence": "LOW",
        "is_fallback": True
    }


def identify_market_state(price_data, tech_data):
    """量化识别市场状态"""
    try:
        df = price_data['full_data']

        # 计算ATR (波动率) - 使用14周期
        high_low = df['high'] - df['low']
        atr = high_low.rolling(14).mean()
        atr_pct = (atr.iloc[-1] / price_data['price']) * 100

        # 获取均线数据
        sma_5 = tech_data.get('sma_5', 0)
        sma_20 = tech_data.get('sma_20', 0)
        sma_50 = tech_data.get('sma_50', 0)

        # 均线排列判断趋势强度
        if sma_5 > sma_20 > sma_50:
            trend_strength = "强上涨"
            confidence = 0.9
        elif sma_5 < sma_20 < sma_50:
            trend_strength = "强下跌"
            confidence = 0.9
        elif abs(sma_5 - sma_20) / sma_20 < 0.005:  # 0.5%以内
            trend_strength = "震荡"
            confidence = 0.7
        else:
            trend_strength = "弱趋势"
            confidence = 0.5

        # 综合判断市场状态
        if atr_pct > 3:  # 高波动
            state = "高波动" + trend_strength
        elif atr_pct < 1:  # 低波动
            state = "低波动震荡"
        else:
            state = trend_strength

        return {
            'state': state,
            'confidence': confidence,
            'atr_pct': atr_pct,
            'trend_strength': trend_strength
        }
    except Exception as e:
        print(f"市场状态识别失败: {e}")
        return {
            'state': '未知',
            'confidence': 0.5,
            'atr_pct': 2.0,
            'trend_strength': '未知'
        }


def calculate_dynamic_tp_sl(signal, current_price, market_state, position=None):
    """基于市场状态动态计算止盈止损"""

    atr_pct = market_state.get('atr_pct', 2.0)  # 波动率

    # 基础止损止盈比例 - 根据市场波动率调整
    if market_state['state'].startswith('高波动'):
        base_sl_pct = 0.025  # 2.5%
        base_tp_pct = 0.06   # 6%
    elif market_state['state'].startswith('低波动'):
        base_sl_pct = 0.015  # 1.5%
        base_tp_pct = 0.03   # 3%
    else:
        base_sl_pct = 0.02   # 2%
        base_tp_pct = 0.05   # 5%

    # 根据信号方向计算
    if signal == 'BUY':
        stop_loss = current_price * (1 - base_sl_pct)
        take_profit = current_price * (1 + base_tp_pct)
    elif signal == 'SELL':
        stop_loss = current_price * (1 + base_sl_pct)
        take_profit = current_price * (1 - base_tp_pct)
    else:  # HOLD
        stop_loss = current_price * 0.98
        take_profit = current_price * 1.02

    # 如果有持仓，考虑移动止损
    if position and position.get('unrealized_pnl', 0) > 0:
        entry_price = position.get('entry_price', current_price)
        position_size = position.get('size', 0)

        if entry_price > 0 and position_size > 0:
            profit_pct = position['unrealized_pnl'] / (entry_price * position_size * 0.01)

            if profit_pct > 0.05:  # 盈利>5%
                # 移动止损到保本+1%
                if position['side'] == 'long':
                    stop_loss = max(stop_loss, entry_price * 1.01)
                else:
                    stop_loss = min(stop_loss, entry_price * 0.99)
                print(f"📈 盈利{profit_pct:.1%}，移动止损到保本+1%: {stop_loss:.2f}")

    return {
        'stop_loss': round(stop_loss, 2),
        'take_profit': round(take_profit, 2),
        'sl_pct': base_sl_pct,
        'tp_pct': base_tp_pct
    }


def validate_ai_signal(ai_signal, price_data, tech_data):
    """量化验证AI信号，防止明显错误"""

    signal = ai_signal.get('signal', 'HOLD')
    tech = tech_data

    # 规则1: RSI极端值检查
    rsi = tech.get('rsi', 50)
    if rsi > 80 and signal == 'BUY':
        print("⚠️ RSI超买(>80)，降低BUY信号信心")
        ai_signal['confidence'] = 'LOW'
        ai_signal['reason'] += " [RSI超买警告]"

    if rsi < 20 and signal == 'SELL':
        print("⚠️ RSI超卖(<20)，降低SELL信号信心")
        ai_signal['confidence'] = 'LOW'
        ai_signal['reason'] += " [RSI超卖警告]"

    # 规则2: 趋势一致性检查
    trend = price_data.get('trend_analysis', {}).get('overall', '震荡整理')
    confidence = ai_signal.get('confidence', 'MEDIUM')

    if trend == "强势上涨" and signal == 'SELL':
        print("⚠️ 强上涨趋势中出现SELL信号，需高信心")
        if confidence != 'HIGH':
            ai_signal['signal'] = 'HOLD'
            ai_signal['reason'] = "趋势与信号冲突，保持观望"
            print("🔄 信号已修正为HOLD")

    if trend == "强势下跌" and signal == 'BUY':
        print("⚠️ 强下跌趋势中出现BUY信号，需高信心")
        if confidence != 'HIGH':
            ai_signal['signal'] = 'HOLD'
            ai_signal['reason'] = "趋势与信号冲突，保持观望"
            print("🔄 信号已修正为HOLD")

    # 规则3: MACD背离检查
    macd = tech.get('macd', 0)
    macd_signal_line = tech.get('macd_signal', 0)

    if macd > macd_signal_line and signal == 'SELL':
        print("⚠️ MACD多头但信号SELL，降低信心")
        if ai_signal.get('confidence') == 'HIGH':
            ai_signal['confidence'] = 'MEDIUM'

    if macd < macd_signal_line and signal == 'BUY':
        print("⚠️ MACD空头但信号BUY，降低信心")
        if ai_signal.get('confidence') == 'HIGH':
            ai_signal['confidence'] = 'MEDIUM'

    # 规则4: 止盈止损合理性检查
    current_price = price_data['price']
    stop_loss = ai_signal.get('stop_loss', 0)
    take_profit = ai_signal.get('take_profit', 0)

    if signal == 'BUY':
        # 止损应该低于当前价
        if stop_loss >= current_price:
            ai_signal['stop_loss'] = current_price * 0.98
            print(f"⚠️ 修正BUY止损价: {ai_signal['stop_loss']:.2f}")
        # 止盈应该高于当前价
        if take_profit <= current_price:
            ai_signal['take_profit'] = current_price * 1.03
            print(f"⚠️ 修正BUY止盈价: {ai_signal['take_profit']:.2f}")

    elif signal == 'SELL':
        # 止损应该高于当前价
        if stop_loss <= current_price:
            ai_signal['stop_loss'] = current_price * 1.02
            print(f"⚠️ 修正SELL止损价: {ai_signal['stop_loss']:.2f}")
        # 止盈应该低于当前价
        if take_profit >= current_price:
            ai_signal['take_profit'] = current_price * 0.97
            print(f"⚠️ 修正SELL止盈价: {ai_signal['take_profit']:.2f}")

    return ai_signal


def analyze_with_deepseek(price_data):
    """使用DeepSeek分析市场并生成交易信号（优化版）"""

    # 生成技术分析文本
    technical_analysis = generate_technical_analysis_text(price_data)

    # 构建K线数据文本
    kline_text = f"【最近5根{TRADE_CONFIG['timeframe']}K线数据】\n"
    for i, kline in enumerate(price_data['kline_data'][-5:]):
        trend = "阳线" if kline['close'] > kline['open'] else "阴线"
        change = ((kline['close'] - kline['open']) / kline['open']) * 100
        kline_text += f"K线{i + 1}: {trend} 开盘:{kline['open']:.2f} 收盘:{kline['close']:.2f} 涨跌:{change:+.2f}%\n"

    # 添加上次交易信号
    signal_text = ""
    if signal_history:
        last_signal = signal_history[-1]
        signal_text = f"\n【上次信号】{last_signal.get('signal', 'N/A')} (信心: {last_signal.get('confidence', 'N/A')})"

    # 获取情绪数据
    sentiment_data = get_sentiment_indicators()
    if sentiment_data:
        sign = '+' if sentiment_data['net_sentiment'] >= 0 else ''
        sentiment_text = f"【市场情绪】乐观{sentiment_data['positive_ratio']:.1%} 悲观{sentiment_data['negative_ratio']:.1%} 净值{sign}{sentiment_data['net_sentiment']:.3f}"
    else:
        sentiment_text = "【市场情绪】数据暂不可用"

    # 添加当前持仓信息
    current_pos = get_current_position()
    position_text = "无持仓" if not current_pos else f"{current_pos['side']}仓, 数量: {current_pos['size']}, 盈亏: {current_pos['unrealized_pnl']:.2f}USDT"
    pnl_text = f", 持仓盈亏: {current_pos['unrealized_pnl']:.2f} USDT" if current_pos else ""

    # 识别市场状态
    tech_data = price_data.get('technical_data', {})
    market_state = identify_market_state(price_data, tech_data)

    # 动态计算建议的止盈止损
    suggested_tp_sl = calculate_dynamic_tp_sl('BUY', price_data['price'], market_state, current_pos)
    tp_sl_hint = f"建议止损±{suggested_tp_sl['sl_pct']*100:.1f}%, 止盈±{suggested_tp_sl['tp_pct']*100:.1f}%"

    # 简化优化的Prompt
    prompt = f"""
你是专业的BTC交易分析师。{TRADE_CONFIG['timeframe']}周期分析：

【核心数据】
价格: ${price_data['price']:,.2f} ({price_data['price_change']:+.2f}%)
市场状态: {market_state['state']} (波动率: {market_state['atr_pct']:.2f}%)
趋势: {price_data['trend_analysis'].get('overall', 'N/A')}
RSI: {price_data['technical_data'].get('rsi', 0):.1f} | MACD: {price_data['trend_analysis'].get('macd', 'N/A')}
持仓: {position_text}
{signal_text}

{kline_text}

{technical_analysis}

{sentiment_text}

【决策规则】
1. 强趋势市场(均线多头/空头排列) → 跟随趋势 BUY/SELL
2. 震荡市场(均线纠缠) → 等待突破 HOLD
3. 反转信号 → 需2+指标确认
4. RSI仅辅助，不作主要依据
5. BTC偏多头，上涨趋势可积极

【止盈止损】
{tp_sl_hint}
- 持仓盈利>5% → 移动止损到保本+1%
- 持仓亏损>3% → 考虑止损

【输出格式】
严格JSON格式：
{{
    "signal": "BUY|SELL|HOLD",
    "reason": "核心理由(30字内)",
    "stop_loss": 具体价格数字,
    "take_profit": 具体价格数字,
    "confidence": "HIGH|MEDIUM|LOW"
}}
"""

    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system",
                 "content": f"您是专业交易员，专注{TRADE_CONFIG['timeframe']}周期趋势分析。严格输出JSON格式，不要添加任何解释文字。"},
                {"role": "user", "content": prompt}
            ],
            stream=False,
            temperature=0.1
        )

        # 安全解析JSON
        result = response.choices[0].message.content
        print(f"🤖 AI原始回复: {result[:200]}...")

        # 提取JSON部分
        start_idx = result.find('{')
        end_idx = result.rfind('}') + 1

        if start_idx != -1 and end_idx != 0:
            json_str = result[start_idx:end_idx]
            signal_data = safe_json_parse(json_str)

            if signal_data is None:
                signal_data = create_fallback_signal(price_data)
        else:
            signal_data = create_fallback_signal(price_data)

        # 验证必需字段
        required_fields = ['signal', 'reason', 'stop_loss', 'take_profit', 'confidence']
        if not all(field in signal_data for field in required_fields):
            signal_data = create_fallback_signal(price_data)

        # 🆕 量化验证AI信号
        print(f"📊 AI原始信号: {signal_data['signal']} (信心: {signal_data['confidence']})")
        signal_data = validate_ai_signal(signal_data, price_data, tech_data)
        print(f"✅ 验证后信号: {signal_data['signal']} (信心: {signal_data['confidence']})")

        # 🆕 使用动态止盈止损（如果AI的不合理）
        dynamic_tp_sl = calculate_dynamic_tp_sl(signal_data['signal'], price_data['price'], market_state, current_pos)

        # 检查AI的止盈止损是否合理，不合理则使用动态计算的
        if signal_data['signal'] != 'HOLD':
            ai_sl = signal_data.get('stop_loss', 0)
            ai_tp = signal_data.get('take_profit', 0)
            current_price = price_data['price']

            # 验证止损止盈的合理性
            sl_valid = False
            tp_valid = False

            if signal_data['signal'] == 'BUY':
                sl_valid = ai_sl < current_price and ai_sl > current_price * 0.95  # 止损在当前价下方且不超过5%
                tp_valid = ai_tp > current_price and ai_tp < current_price * 1.10  # 止盈在当前价上方且不超过10%
            elif signal_data['signal'] == 'SELL':
                sl_valid = ai_sl > current_price and ai_sl < current_price * 1.05  # 止损在当前价上方且不超过5%
                tp_valid = ai_tp < current_price and ai_tp > current_price * 0.90  # 止盈在当前价下方且不超过10%

            if not sl_valid or not tp_valid:
                print(f"⚠️ AI止盈止损不合理，使用动态计算: SL={dynamic_tp_sl['stop_loss']}, TP={dynamic_tp_sl['take_profit']}")
                signal_data['stop_loss'] = dynamic_tp_sl['stop_loss']
                signal_data['take_profit'] = dynamic_tp_sl['take_profit']

        # 保存信号到历史记录
        signal_data['timestamp'] = price_data['timestamp']
        signal_history.append(signal_data)
        if len(signal_history) > 30:
            signal_history.pop(0)

        # 信号统计
        signal_count = len([s for s in signal_history if s.get('signal') == signal_data['signal']])
        total_signals = len(signal_history)
        print(f"信号统计: {signal_data['signal']} (最近{total_signals}次中出现{signal_count}次)")

        # 信号连续性检查
        if len(signal_history) >= 3:
            last_three = [s['signal'] for s in signal_history[-3:]]
            if len(set(last_three)) == 1:
                print(f"⚠️ 注意：连续3次{signal_data['signal']}信号")

        return signal_data

    except Exception as e:
        print(f"DeepSeek分析失败: {e}")
        return create_fallback_signal(price_data)


def get_active_tp_sl_orders():
    """
    查询当前活跃的止盈止损订单

    返回:
        dict: 包含止盈止损订单信息的字典
    """
    try:
        # 转换交易对格式：BTC/USDT:USDT -> BTC-USDT-SWAP
        inst_id = TRADE_CONFIG['symbol'].replace('/USDT:USDT', '-USDT-SWAP').replace('/', '-')

        # 使用OKX专用的算法订单API查询
        response = exchange.private_get_trade_orders_algo_pending({
            'instType': 'SWAP',
            'instId': inst_id,
            'ordType': 'conditional'  # 查询条件单
        })

        active_orders = {
            'stop_loss_orders': [],
            'take_profit_orders': []
        }

        if response.get('code') == '0' and response.get('data'):
            for order in response['data']:
                ord_type = order.get('ordType')

                # 检查是否是止盈止损订单
                if ord_type == 'conditional':
                    # 判断是止损还是止盈
                    if order.get('slTriggerPx'):
                        active_orders['stop_loss_orders'].append({
                            'order_id': order['algoId'],
                            'trigger_price': float(order['slTriggerPx']),
                            'size': float(order['sz']),
                            'side': order['side'],
                            'state': order['state']
                        })
                    elif order.get('tpTriggerPx'):
                        active_orders['take_profit_orders'].append({
                            'order_id': order['algoId'],
                            'trigger_price': float(order['tpTriggerPx']),
                            'size': float(order['sz']),
                            'side': order['side'],
                            'state': order['state']
                        })

        return active_orders

    except Exception as e:
        print(f"⚠️ 查询止盈止损订单失败: {e}")
        return {'stop_loss_orders': [], 'take_profit_orders': []}


def cancel_existing_tp_sl_orders():
    """取消现有的止盈止损订单"""
    global active_tp_sl_orders

    try:
        # 转换交易对格式：BTC/USDT:USDT -> BTC-USDT-SWAP
        inst_id = TRADE_CONFIG['symbol'].replace('/USDT:USDT', '-USDT-SWAP').replace('/', '-')

        # 使用OKX专用的算法订单API
        # 获取所有活跃的算法订单（止盈止损订单）
        try:
            # OKX的算法订单查询
            response = exchange.private_get_trade_orders_algo_pending({
                'instType': 'SWAP',
                'instId': inst_id,
                'ordType': 'conditional'  # 查询条件单
            })

            if response.get('code') == '0' and response.get('data'):
                for order in response['data']:
                    # 检查是否是止盈止损订单
                    ord_type = order.get('ordType')
                    if ord_type in ['conditional', 'oco']:
                        try:
                            # 取消算法订单 - 使用正确的格式
                            cancel_response = exchange.private_post_trade_cancel_algos({
                                'params': [{
                                    'algoId': order['algoId'],
                                    'instId': inst_id  # ✅ 修复：使用正确的格式 BTC-USDT-SWAP
                                }]
                            })

                            if cancel_response.get('code') == '0':
                                print(f"✅ 已取消旧的止盈止损订单: {order['algoId']}")
                            else:
                                print(f"⚠️ 取消订单失败: {cancel_response.get('msg')}")
                        except Exception as e:
                            print(f"⚠️ 取消订单异常 {order.get('algoId')}: {e}")
        except Exception as e:
            print(f"⚠️ 查询算法订单失败: {e}")

        # 重置全局变量
        active_tp_sl_orders['take_profit_order_id'] = None
        active_tp_sl_orders['stop_loss_order_id'] = None

    except Exception as e:
        print(f"⚠️ 取消止盈止损订单时出错: {e}")


def check_existing_tp_sl_orders(position_side, stop_loss_price, take_profit_price, position_size):
    """
    检查是否已存在相同的止盈止损订单，避免重复创建

    返回: True=已存在相同订单，False=需要创建新订单
    """
    try:
        inst_id = TRADE_CONFIG['symbol'].replace('/USDT:USDT', '-USDT-SWAP').replace('/', '-')

        # 查询当前活跃的算法订单
        response = exchange.private_get_trade_orders_algo_pending({
            'instType': 'SWAP',
            'instId': inst_id,
            'ordType': 'conditional'
        })

        if response.get('code') == '0' and response.get('data'):
            orders = response['data']

            # 检查是否有匹配的订单
            has_sl = False
            has_tp = False

            for order in orders:
                # 检查订单方向和数量是否匹配
                order_side = order.get('side')
                order_sz = float(order.get('sz', 0))

                # 平仓方向应该与持仓相反
                expected_side = 'sell' if position_side == 'long' else 'buy'

                if order_side == expected_side and abs(order_sz - position_size) < 0.01:
                    # 检查止损订单
                    if order.get('slTriggerPx'):
                        sl_trigger = float(order['slTriggerPx'])
                        if abs(sl_trigger - stop_loss_price) < 1:  # 价格差异小于1美元
                            has_sl = True

                    # 检查止盈订单
                    if order.get('tpTriggerPx'):
                        tp_trigger = float(order['tpTriggerPx'])
                        if abs(tp_trigger - take_profit_price) < 1:  # 价格差异小于1美元
                            has_tp = True

            # 如果止损和止盈订单都已存在，返回True
            if has_sl and has_tp:
                print(f"ℹ️ 止盈止损订单已存在，无需重复创建")
                return True

        return False

    except Exception as e:
        print(f"⚠️ 检查订单失败: {e}")
        return False


def set_stop_loss_take_profit(position_side, stop_loss_price, take_profit_price, position_size, force_update=False):
    """
    设置止盈止损订单 - 使用OKX算法订单API

    参数:
        position_side: 'long' 或 'short'
        stop_loss_price: 止损价格
        take_profit_price: 止盈价格
        position_size: 持仓数量
        force_update: 是否强制更新（默认False，会检查是否已存在相同订单）
    """
    global active_tp_sl_orders

    try:
        # 转换交易对格式：BTC/USDT:USDT -> BTC-USDT-SWAP
        inst_id = TRADE_CONFIG['symbol'].replace('/USDT:USDT', '-USDT-SWAP').replace('/', '-')

        # 🆕 如果不是强制更新，先检查是否已存在相同订单
        if not force_update:
            if check_existing_tp_sl_orders(position_side, stop_loss_price, take_profit_price, position_size):
                return True  # 订单已存在，无需重复创建

        # 取消现有的止盈止损订单
        cancel_existing_tp_sl_orders()

        # 确定订单方向（平仓方向与开仓相反）
        close_side = 'sell' if position_side == 'long' else 'buy'

        # 使用OKX的算法订单API设置止盈止损
        # 方法1: 使用单独的止损和止盈订单

        # 设置止损订单 (Stop Loss)
        if stop_loss_price:
            try:
                # 使用OKX的条件单API
                sl_params = {
                    'instId': inst_id,
                    'tdMode': 'cross',  # 全仓模式
                    'side': close_side,
                    'ordType': 'conditional',  # 条件单
                    'sz': str(position_size),
                    'slTriggerPx': str(stop_loss_price),  # 止损触发价
                    'slOrdPx': '-1',  # 市价单（-1表示市价）
                    'reduceOnly': 'true',  # 只减仓
                    'tag': 'c314b0aecb5bBCDE'  # 节点（默认，无需改动）
                }

                # 调用OKX的算法订单API
                response = exchange.private_post_trade_order_algo(sl_params)

                if response.get('code') == '0' and response.get('data'):
                    algo_id = response['data'][0]['algoId']
                    active_tp_sl_orders['stop_loss_order_id'] = algo_id
                    print(f"✅ 止损订单已设置: 触发价={stop_loss_price}, 订单ID={algo_id}")
                else:
                    print(f"❌ 设置止损订单失败: {response.get('msg')}")

            except Exception as e:
                print(f"❌ 设置止损订单失败: {e}")

        # 设置止盈订单 (Take Profit)
        if take_profit_price:
            try:
                # 使用OKX的条件单API
                tp_params = {
                    'instId': inst_id,
                    'tdMode': 'cross',  # 全仓模式
                    'side': close_side,
                    'ordType': 'conditional',  # 条件单
                    'sz': str(position_size),
                    'tpTriggerPx': str(take_profit_price),  # 止盈触发价
                    'tpOrdPx': '-1',  # 市价单（-1表示市价）
                    'reduceOnly': 'true',  # 只减仓
                    'tag': 'c314b0aecb5bBCDE'  # 节点（默认，无需改动）
                }

                # 调用OKX的算法订单API
                response = exchange.private_post_trade_order_algo(tp_params)

                if response.get('code') == '0' and response.get('data'):
                    algo_id = response['data'][0]['algoId']
                    active_tp_sl_orders['take_profit_order_id'] = algo_id
                    print(f"✅ 止盈订单已设置: 触发价={take_profit_price}, 订单ID={algo_id}")
                else:
                    print(f"❌ 设置止盈订单失败: {response.get('msg')}")

            except Exception as e:
                print(f"❌ 设置止盈订单失败: {e}")

        return True

    except Exception as e:
        print(f"❌ 设置止盈止损失败: {e}")
        return False


def execute_intelligent_trade(signal_data, price_data):
    """执行智能交易 - OKX版本（支持同方向加仓减仓）"""
    global position

    current_position = get_current_position()

    # 防止频繁反转的逻辑保持不变
    if current_position and signal_data['signal'] != 'HOLD':
        current_side = current_position['side']  # 'long' 或 'short'

        if signal_data['signal'] == 'BUY':
            new_side = 'long'
        elif signal_data['signal'] == 'SELL':
            new_side = 'short'
        else:
            new_side = None

        # 如果方向相反，需要高信心才执行
        # if new_side != current_side:
        #     if signal_data['confidence'] != 'HIGH':
        #         print(f"🔒 非高信心反转信号，保持现有{current_side}仓")
        #         return

        #     if len(signal_history) >= 2:
        #         last_signals = [s['signal'] for s in signal_history[-2:]]
        #         if signal_data['signal'] in last_signals:
        #             print(f"🔒 近期已出现{signal_data['signal']}信号，避免频繁反转")
        #             return

    # 计算智能仓位
    position_size = calculate_intelligent_position(signal_data, price_data, current_position)

    print(f"交易信号: {signal_data['signal']}")
    print(f"信心程度: {signal_data['confidence']}")
    print(f"智能仓位: {position_size:.2f} 张")
    print(f"理由: {signal_data['reason']}")
    print(f"当前持仓: {current_position}")

    # 风险管理
    if signal_data['confidence'] == 'LOW' and not TRADE_CONFIG['test_mode']:
        print("⚠️ 低信心信号，跳过执行")
        return

    if TRADE_CONFIG['test_mode']:
        print("测试模式 - 仅模拟交易")
        return

    try:
        # 执行交易逻辑 - 支持同方向加仓减仓
        if signal_data['signal'] == 'BUY':
            if current_position and current_position['side'] == 'short':
                # 先检查空头持仓是否真实存在且数量正确
                if current_position['size'] > 0:
                    print(f"平空仓 {current_position['size']:.2f} 张并开多仓 {position_size:.2f} 张...")
                    # 取消现有的止盈止损订单
                    cancel_existing_tp_sl_orders()
                    # 平空仓
                    exchange.create_market_order(
                        TRADE_CONFIG['symbol'],
                        'buy',
                        current_position['size'],
                        params={'reduceOnly': True, 'tag': 'c314b0aecb5bBCDE'}
                    )
                    time.sleep(1)
                    # 开多仓
                    exchange.create_market_order(
                        TRADE_CONFIG['symbol'],
                        'buy',
                        position_size,
                        params={'tag': 'c314b0aecb5bBCDE'}
                    )
                else:
                    print("⚠️ 检测到空头持仓但数量为0，直接开多仓")
                    exchange.create_market_order(
                        TRADE_CONFIG['symbol'],
                        'buy',
                        position_size,
                        params={'tag': 'c314b0aecb5bBCDE'}
                    )

            elif current_position and current_position['side'] == 'long':
                # 同方向，检查是否需要调整仓位
                size_diff = position_size - current_position['size']

                if abs(size_diff) >= 0.01:  # 有可调整的差异
                    if size_diff > 0:
                        # 加仓
                        add_size = round(size_diff, 2)
                        print(
                            f"多仓加仓 {add_size:.2f} 张 (当前:{current_position['size']:.2f} → 目标:{position_size:.2f})")
                        exchange.create_market_order(
                            TRADE_CONFIG['symbol'],
                            'buy',
                            add_size,
                            params={'tag': 'c314b0aecb5bBCDE'}
                        )
                    else:
                        # 减仓
                        reduce_size = round(abs(size_diff), 2)
                        print(
                            f"多仓减仓 {reduce_size:.2f} 张 (当前:{current_position['size']:.2f} → 目标:{position_size:.2f})")
                        exchange.create_market_order(
                            TRADE_CONFIG['symbol'],
                            'sell',
                            reduce_size,
                            params={'reduceOnly': True, 'tag': 'c314b0aecb5bBCDE'}
                        )
                else:
                    print(
                        f"已有多头持仓，仓位合适保持现状 (当前:{current_position['size']:.2f}, 目标:{position_size:.2f})")
            else:
                # 无持仓时开多仓
                print(f"开多仓 {position_size:.2f} 张...")
                exchange.create_market_order(
                    TRADE_CONFIG['symbol'],
                    'buy',
                    position_size,
                    params={'tag': 'c314b0aecb5bBCDE'}
                )

        elif signal_data['signal'] == 'SELL':
            if current_position and current_position['side'] == 'long':
                # 先检查多头持仓是否真实存在且数量正确
                if current_position['size'] > 0:
                    print(f"平多仓 {current_position['size']:.2f} 张并开空仓 {position_size:.2f} 张...")
                    # 取消现有的止盈止损订单
                    cancel_existing_tp_sl_orders()
                    # 平多仓
                    exchange.create_market_order(
                        TRADE_CONFIG['symbol'],
                        'sell',
                        current_position['size'],
                        params={'reduceOnly': True, 'tag': 'c314b0aecb5bBCDE'}
                    )
                    time.sleep(1)
                    # 开空仓
                    exchange.create_market_order(
                        TRADE_CONFIG['symbol'],
                        'sell',
                        position_size,
                        params={'tag': 'c314b0aecb5bBCDE'}
                    )
                else:
                    print("⚠️ 检测到多头持仓但数量为0，直接开空仓")
                    exchange.create_market_order(
                        TRADE_CONFIG['symbol'],
                        'sell',
                        position_size,
                        params={'tag': 'c314b0aecb5bBCDE'}
                    )

            elif current_position and current_position['side'] == 'short':
                # 同方向，检查是否需要调整仓位
                size_diff = position_size - current_position['size']

                if abs(size_diff) >= 0.01:  # 有可调整的差异
                    if size_diff > 0:
                        # 加仓
                        add_size = round(size_diff, 2)
                        print(
                            f"空仓加仓 {add_size:.2f} 张 (当前:{current_position['size']:.2f} → 目标:{position_size:.2f})")
                        exchange.create_market_order(
                            TRADE_CONFIG['symbol'],
                            'sell',
                            add_size,
                            params={'tag': 'c314b0aecb5bBCDE'}
                        )
                    else:
                        # 减仓
                        reduce_size = round(abs(size_diff), 2)
                        print(
                            f"空仓减仓 {reduce_size:.2f} 张 (当前:{current_position['size']:.2f} → 目标:{position_size:.2f})")
                        exchange.create_market_order(
                            TRADE_CONFIG['symbol'],
                            'buy',
                            reduce_size,
                            params={'reduceOnly': True, 'tag': 'c314b0aecb5bBCDE'}
                        )
                else:
                    print(
                        f"已有空头持仓，仓位合适保持现状 (当前:{current_position['size']:.2f}, 目标:{position_size:.2f})")
            else:
                # 无持仓时开空仓
                print(f"开空仓 {position_size:.2f} 张...")
                exchange.create_market_order(
                    TRADE_CONFIG['symbol'],
                    'sell',
                    position_size,
                    params={'tag': 'c314b0aecb5bBCDE'}
                )

        elif signal_data['signal'] == 'HOLD':
            print("建议观望，不执行交易")
            # 🆕 优化：如果有持仓，检查止盈止损订单是否存在，不存在才创建
            if current_position and current_position['size'] > 0:
                stop_loss_price = signal_data.get('stop_loss')
                take_profit_price = signal_data.get('take_profit')

                # 只有当止盈止损价格有效时才处理
                if stop_loss_price and take_profit_price:
                    # 检查是否已存在订单（不强制更新）
                    if not check_existing_tp_sl_orders(
                        current_position['side'],
                        stop_loss_price,
                        take_profit_price,
                        current_position['size']
                    ):
                        print(f"\n📊 创建止盈止损订单:")
                        print(f"   止损价格: {stop_loss_price}")
                        print(f"   止盈价格: {take_profit_price}")

                        set_stop_loss_take_profit(
                            position_side=current_position['side'],
                            stop_loss_price=stop_loss_price,
                            take_profit_price=take_profit_price,
                            position_size=current_position['size'],
                            force_update=False  # 不强制更新
                        )
                    else:
                        print(f"ℹ️ 止盈止损订单已存在，无需更新")
            return

        print("智能交易执行成功")
        time.sleep(2)
        position = get_current_position()
        print(f"更新后持仓: {position}")

        # 🆕 交易后设置止盈止损订单（强制更新）
        if position and position['size'] > 0:
            stop_loss_price = signal_data.get('stop_loss')
            take_profit_price = signal_data.get('take_profit')

            if stop_loss_price or take_profit_price:
                print(f"\n📊 设置止盈止损:")
                print(f"   止损价格: {stop_loss_price}")
                print(f"   止盈价格: {take_profit_price}")

                set_stop_loss_take_profit(
                    position_side=position['side'],
                    stop_loss_price=stop_loss_price,
                    take_profit_price=take_profit_price,
                    position_size=position['size'],
                    force_update=True  # 交易后强制更新订单
                )

        # 保存交易记录
        try:
            # 计算实际盈亏（如果有持仓）
            pnl = 0
            if current_position and position:
                # 如果方向改变或平仓，计算盈亏
                if current_position['side'] != position.get('side'):
                    if current_position['side'] == 'long':
                        pnl = (price_data['price'] - current_position['entry_price']) * current_position['size'] * TRADE_CONFIG.get('contract_size', 0.01)
                    else:
                        pnl = (current_position['entry_price'] - price_data['price']) * current_position['size'] * TRADE_CONFIG.get('contract_size', 0.01)
            
            trade_record = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'signal': signal_data['signal'],
                'price': price_data['price'],
                'amount': position_size,
                'confidence': signal_data['confidence'],
                'reason': signal_data['reason'],
                'pnl': pnl
            }
            save_trade_record(trade_record)
            print("✅ 交易记录已保存")
        except Exception as e:
            print(f"保存交易记录失败: {e}")

    except Exception as e:
        print(f"交易执行失败: {e}")

        # 如果是持仓不存在的错误，尝试直接开新仓
        if "don't have any positions" in str(e):
            print("尝试直接开新仓...")
            try:
                if signal_data['signal'] == 'BUY':
                    exchange.create_market_order(
                        TRADE_CONFIG['symbol'],
                        'buy',
                        position_size,
                        params={'tag': 'c314b0aecb5bBCDE'}
                    )
                elif signal_data['signal'] == 'SELL':
                    exchange.create_market_order(
                        TRADE_CONFIG['symbol'],
                        'sell',
                        position_size,
                        params={'tag': 'c314b0aecb5bBCDE'}
                    )
                print("直接开仓成功")
            except Exception as e2:
                print(f"直接开仓也失败: {e2}")

        import traceback
        traceback.print_exc()


def analyze_with_deepseek_with_retry(price_data, max_retries=2):
    """带重试的DeepSeek分析"""
    for attempt in range(max_retries):
        try:
            signal_data = analyze_with_deepseek(price_data)
            if signal_data and not signal_data.get('is_fallback', False):
                return signal_data

            print(f"第{attempt + 1}次尝试失败，进行重试...")
            time.sleep(1)

        except Exception as e:
            print(f"第{attempt + 1}次尝试异常: {e}")
            if attempt == max_retries - 1:
                return create_fallback_signal(price_data)
            time.sleep(1)

    return create_fallback_signal(price_data)


def wait_for_next_period():
    """等待到下一个15分钟整点"""
    now = datetime.now()
    current_minute = now.minute
    current_second = now.second

    # 计算下一个整点时间（00, 15, 30, 45分钟）
    next_period_minute = ((current_minute // 15) + 1) * 15
    if next_period_minute == 60:
        next_period_minute = 0

    # 计算需要等待的总秒数
    if next_period_minute > current_minute:
        minutes_to_wait = next_period_minute - current_minute
    else:
        minutes_to_wait = 60 - current_minute + next_period_minute

    seconds_to_wait = minutes_to_wait * 60 - current_second

    # 显示友好的等待时间
    display_minutes = minutes_to_wait - 1 if current_second > 0 else minutes_to_wait
    display_seconds = 60 - current_second if current_second > 0 else 0

    if display_minutes > 0:
        print(f"🕒 等待 {display_minutes} 分 {display_seconds} 秒到整点...")
    else:
        print(f"🕒 等待 {display_seconds} 秒到整点...")

    return seconds_to_wait


def trading_bot():
    # 等待到整点再执行
    wait_seconds = wait_for_next_period()
    if wait_seconds > 0:
        time.sleep(wait_seconds)

    """主交易机器人函数"""
    print("\n" + "=" * 60)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 获取增强版K线数据
    price_data = get_btc_ohlcv_enhanced()
    if not price_data:
        return

    print(f"BTC当前价格: ${price_data['price']:,.2f}")
    print(f"数据周期: {TRADE_CONFIG['timeframe']}")
    print(f"价格变化: {price_data['price_change']:+.2f}%")

    # 2. 获取账户信息
    try:
        balance = exchange.fetch_balance()
        account_info = {
            'balance': float(balance['USDT'].get('free', 0)),
            'equity': float(balance['USDT'].get('total', 0)),
            'leverage': TRADE_CONFIG['leverage']
        }
    except Exception as e:
        print(f"获取账户信息失败: {e}")
        account_info = None

    # 3. 获取当前持仓
    current_position = get_current_position()
    position_info = None
    if current_position:
        position_info = {
            'side': current_position['side'],
            'size': current_position['size'],
            'entry_price': current_position['entry_price'],
            'unrealized_pnl': current_position['unrealized_pnl']
        }

    # 4. 使用DeepSeek分析（带重试）
    signal_data = analyze_with_deepseek_with_retry(price_data)

    if signal_data.get('is_fallback', False):
        print("⚠️ 使用备用交易信号")

    # 5. 更新系统状态到Web界面
    try:
        update_system_status(
            status='running',
            account_info=account_info,
            btc_info={
                'price': price_data['price'],
                'change': price_data['price_change'],
                'timeframe': TRADE_CONFIG['timeframe'],
                'mode': '全仓-单向'
            },
            position=position_info,
            ai_signal={
                'signal': signal_data['signal'],
                'confidence': signal_data['confidence'],
                'reason': signal_data['reason'],
                'stop_loss': signal_data['stop_loss'],
                'take_profit': signal_data['take_profit']
            },
            tp_sl_orders={
                'stop_loss_order_id': active_tp_sl_orders.get('stop_loss_order_id'),
                'take_profit_order_id': active_tp_sl_orders.get('take_profit_order_id')
            }
        )
        print("✅ 系统状态已更新到Web界面")
    except Exception as e:
        print(f"更新系统状态失败: {e}")

    # 6. 执行智能交易
    execute_intelligent_trade(signal_data, price_data)


def main():
    """主函数"""
    print("BTC/USDT OKX自动交易机器人启动成功！")
    print("融合技术指标策略 + OKX实盘接口")

    if TRADE_CONFIG['test_mode']:
        print("当前为模拟模式，不会真实下单")
    else:
        print("实盘交易模式，请谨慎操作！")

    print(f"交易周期: {TRADE_CONFIG['timeframe']}")
    print("已启用完整技术指标分析和持仓跟踪功能")

    # 设置交易所
    if not setup_exchange():
        print("交易所初始化失败，程序退出")
        return
    
    # 初始化Web界面数据文件
    print("🌐 初始化Web界面数据...")
    try:
        # 获取初始账户信息
        balance = exchange.fetch_balance()
        initial_account = {
            'balance': float(balance['USDT'].get('free', 0)),
            'equity': float(balance['USDT'].get('total', 0)),
            'leverage': TRADE_CONFIG['leverage']
        }
        
        # 获取当前BTC价格
        ticker = exchange.fetch_ticker(TRADE_CONFIG['symbol'])
        initial_btc = {
            'price': float(ticker['last']),
            'change': float(ticker['percentage']) if ticker.get('percentage') else 0,
            'timeframe': TRADE_CONFIG['timeframe'],
            'mode': '全仓-单向'
        }
        
        # 获取当前持仓
        current_pos = get_current_position()
        initial_position = None
        if current_pos:
            initial_position = {
                'side': current_pos['side'],
                'size': current_pos['size'],
                'entry_price': current_pos['entry_price'],
                'unrealized_pnl': current_pos['unrealized_pnl']
            }
        
        # 初始化系统状态
        update_system_status(
            status='running',
            account_info=initial_account,
            btc_info=initial_btc,
            position=initial_position,
            ai_signal={
                'signal': 'HOLD',
                'confidence': 'N/A',
                'reason': '系统启动中，等待首次分析...',
                'stop_loss': 0,
                'take_profit': 0
            }
        )
        print("✅ Web界面数据初始化完成")
    except Exception as e:
        print(f"⚠️ Web界面数据初始化失败: {e}")
        print("继续运行，将在首次交易时创建数据")

    print("执行频率: 每15分钟整点执行")

    # 循环执行（不使用schedule）
    while True:
        trading_bot()  # 函数内部会自己等待整点

        # 执行完后等待一段时间再检查（避免频繁循环）
        time.sleep(60)  # 每分钟检查一次


if __name__ == "__main__":
    main()