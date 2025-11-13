import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import os

# 页面配置
st.set_page_config(
    page_title="BTC自动交易机器人 - AI量化交易平台",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS样式 - 高端深色主题
st.markdown("""
<style>
    /* 全局样式 */
    .main {
        padding: 0rem 1rem;
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }
    
    /* 标题样式 */
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        text-shadow: 0 0 30px rgba(102, 126, 234, 0.5);
    }
    
    h2, h3 {
        color: #e0e0e0;
        font-weight: 600;
    }
    
    /* 指标卡片 */
    .stMetric {
        background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid rgba(102, 126, 234, 0.2);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        backdrop-filter: blur(4px);
    }
    
    .stMetric label {
        color: #b0b0b0 !important;
        font-size: 14px !important;
        font-weight: 500 !important;
    }
    
    .stMetric [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 24px !important;
        font-weight: 700 !important;
    }
    
    /* 状态卡片 - 运行中 */
    .status-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 25px;
        box-shadow: 0 8px 32px 0 rgba(102, 126, 234, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }
    
    /* 状态卡片 - 成功 */
    .success-card {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 25px;
        box-shadow: 0 8px 32px 0 rgba(56, 239, 125, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }
    
    /* 状态卡片 - 警告 */
    .warning-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 25px;
        box-shadow: 0 8px 32px 0 rgba(245, 87, 108, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }
    
    /* 信息卡片 */
    .info-card {
        background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 15px;
        border: 1px solid rgba(102, 126, 234, 0.2);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    
    .info-card p {
        color: #e0e0e0;
        margin: 5px 0;
    }
    
    /* AI决策卡片 */
    .ai-card-buy {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 15px;
        box-shadow: 0 8px 32px 0 rgba(56, 239, 125, 0.5);
        border: 2px solid rgba(56, 239, 125, 0.3);
        animation: glow-green 2s ease-in-out infinite alternate;
    }
    
    .ai-card-sell {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 15px;
        box-shadow: 0 8px 32px 0 rgba(245, 87, 108, 0.5);
        border: 2px solid rgba(245, 87, 108, 0.3);
        animation: glow-red 2s ease-in-out infinite alternate;
    }
    
    .ai-card-hold {
        background: linear-gradient(135deg, #ffd93d 0%, #ff9a3d 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 15px;
        box-shadow: 0 8px 32px 0 rgba(255, 217, 61, 0.5);
        border: 2px solid rgba(255, 217, 61, 0.3);
    }
    
    @keyframes glow-green {
        from { box-shadow: 0 8px 32px 0 rgba(56, 239, 125, 0.3); }
        to { box-shadow: 0 8px 32px 0 rgba(56, 239, 125, 0.7); }
    }
    
    @keyframes glow-red {
        from { box-shadow: 0 8px 32px 0 rgba(245, 87, 108, 0.3); }
        to { box-shadow: 0 8px 32px 0 rgba(245, 87, 108, 0.7); }
    }
    
    /* 按钮样式 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 600;
        box-shadow: 0 4px 15px 0 rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        box-shadow: 0 6px 20px 0 rgba(102, 126, 234, 0.6);
        transform: translateY(-2px);
    }
    
    /* 数据表格样式 */
    .stDataFrame {
        background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
        border-radius: 15px;
        padding: 10px;
    }
    
    /* 滚动条样式 */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1e1e2e;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* 复选框和输入框 */
    .stCheckbox {
        color: #e0e0e0 !important;
    }
    
    /* 霓虹文字效果 */
    .neon-text {
        color: #fff;
        text-shadow: 
            0 0 7px #fff,
            0 0 10px #fff,
            0 0 21px #fff,
            0 0 42px #667eea,
            0 0 82px #667eea,
            0 0 92px #667eea,
            0 0 102px #667eea,
            0 0 151px #667eea;
    }
    
    /* 价格显示 */
    .price-big {
        font-size: 36px;
        font-weight: 800;
        background: linear-gradient(135deg, #ffd93d 0%, #ff9a3d 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* 盈亏颜色 */
    .profit {
        color: #38ef7d;
        font-weight: 700;
    }
    
    .loss {
        color: #f5576c;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# 数据文件路径
DATA_FILE = "trading_data.json"
TRADES_FILE = "trades_history.json"

def load_trading_data():
    """加载交易数据"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 确保数据完整性
                if 'last_update' in data:
                    # 检查数据是否过期（超过30分钟）
                    try:
                        last_update = datetime.strptime(data['last_update'], '%Y-%m-%d %H:%M:%S')
                        time_diff = (datetime.now() - last_update).total_seconds() / 60
                        if time_diff > 30:
                            data['status'] = 'warning'
                    except:
                        pass
                return data
        else:
            return {
                "status": "stopped",
                "last_update": "N/A",
                "account": {
                    "balance": 0,
                    "equity": 0,
                    "leverage": 0
                },
                "btc": {
                    "price": 0,
                    "change": 0,
                    "timeframe": "1h",
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
                    "reason": "等待交易程序启动...",
                    "stop_loss": 0,
                    "take_profit": 0,
                    "timestamp": "N/A"
                },
                "file_not_found": True
            }
    except Exception as e:
        st.error(f"加载数据失败: {e}")
        return None

def load_trades_history():
    """加载交易历史"""
    try:
        if os.path.exists(TRADES_FILE):
            with open(TRADES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return []
    except Exception as e:
        st.error(f"加载交易历史失败: {e}")
        return []

def create_equity_chart():
    """创建账户总权益曲线图 - 高端深色主题"""
    try:
        # 导入数据管理函数
        from data_manager import load_equity_history

        equity_history = load_equity_history()

        if not equity_history or len(equity_history) == 0:
            fig = go.Figure()
            fig.add_annotation(
                text="暂无权益数据",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=20, color="#667eea")
            )
            fig.update_layout(
                height=400,
                xaxis=dict(showgrid=False, showticklabels=False),
                yaxis=dict(showgrid=False, showticklabels=False),
                plot_bgcolor='rgba(30, 30, 46, 0.6)',
                paper_bgcolor='rgba(0,0,0,0)',
            )
            return fig

        df = pd.DataFrame(equity_history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # 计算初始权益和当前权益
        initial_equity = df['equity'].iloc[0]
        current_equity = df['equity'].iloc[-1]
        equity_change = current_equity - initial_equity
        equity_change_pct = (equity_change / initial_equity * 100) if initial_equity > 0 else 0

        # 确定颜色（根据盈亏）
        line_color = '#38ef7d' if equity_change >= 0 else '#f5576c'
        fill_color = 'rgba(56, 239, 125, 0.2)' if equity_change >= 0 else 'rgba(245, 87, 108, 0.2)'

        fig = go.Figure()

        # 添加账户总权益曲线
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['equity'],
            mode='lines+markers',
            name='账户总权益',
            line=dict(color=line_color, width=3, shape='spline'),
            fill='tozeroy',
            fillcolor=fill_color,
            marker=dict(
                size=8,
                color=line_color,
                line=dict(color='white', width=2)
            ),
            hovertemplate='<b>时间</b>: %{x}<br><b>总权益</b>: %{y:.2f} USDT<extra></extra>'
        ))

        # 添加初始权益基准线
        fig.add_hline(
            y=initial_equity,
            line_dash="dash",
            line_color="rgba(255, 255, 255, 0.3)",
            line_width=2,
            annotation_text=f"初始: {initial_equity:.2f} USDT",
            annotation_position="right"
        )

        fig.update_layout(
            title=dict(
                text=f"💰 账户总权益曲线 ({equity_change:+.2f} USDT / {equity_change_pct:+.2f}%)",
                font=dict(size=24, color='#e0e0e0', family="Arial Black"),
                x=0.5,
                xanchor='center'
            ),
            xaxis=dict(
                title="时间",
                showgrid=True,
                gridcolor='rgba(255, 255, 255, 0.1)',
                color='#b0b0b0',
                title_font=dict(size=14, color='#b0b0b0')
            ),
            yaxis=dict(
                title="总权益 (USDT)",
                showgrid=True,
                gridcolor='rgba(255, 255, 255, 0.1)',
                color='#b0b0b0',
                title_font=dict(size=14, color='#b0b0b0')
            ),
            height=450,
            hovermode='x unified',
            showlegend=False,
            plot_bgcolor='rgba(30, 30, 46, 0.6)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0'),
            margin=dict(l=60, r=40, t=60, b=60)
        )

        return fig

    except Exception as e:
        # 出错时返回空图表
        fig = go.Figure()
        fig.add_annotation(
            text=f"加载权益数据失败: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#f5576c")
        )
        fig.update_layout(
            height=400,
            plot_bgcolor='rgba(30, 30, 46, 0.6)',
            paper_bgcolor='rgba(0,0,0,0)',
        )
        return fig

def create_signal_distribution_chart(trades_history):
    """创建信号分布饼图 - 高端深色主题"""
    if not trades_history:
        fig = go.Figure()
        fig.add_annotation(
            text="暂无数据",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#667eea")
        )
        fig.update_layout(
            height=300,
            plot_bgcolor='rgba(30, 30, 46, 0.6)',
            paper_bgcolor='rgba(0,0,0,0)',
        )
        return fig
    
    df = pd.DataFrame(trades_history)
    signal_counts = df['signal'].value_counts()
    
    colors = {'BUY': '#38ef7d', 'SELL': '#f5576c', 'HOLD': '#ffd93d'}
    
    fig = go.Figure(data=[go.Pie(
        labels=signal_counts.index,
        values=signal_counts.values,
        marker=dict(
            colors=[colors.get(s, '#667eea') for s in signal_counts.index],
            line=dict(color='rgba(255, 255, 255, 0.2)', width=2)
        ),
        hole=0.5,
        textinfo='label+percent',
        textfont=dict(size=14, color='white', family='Arial Black'),
        hovertemplate='<b>%{label}</b><br>数量: %{value}<br>占比: %{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title=dict(
            text="🎯 信号分布",
            font=dict(size=20, color='#e0e0e0', family="Arial Black"),
            x=0.5,
            xanchor='center'
        ),
        height=300,
        showlegend=True,
        legend=dict(
            font=dict(color='#e0e0e0', size=12),
            bgcolor='rgba(30, 30, 46, 0.6)',
            bordercolor='rgba(102, 126, 234, 0.3)',
            borderwidth=1
        ),
        plot_bgcolor='rgba(30, 30, 46, 0.6)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    return fig

def main():
    # 初始化session state
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    # 标题
    st.title("🤖 BTC自动交易机器人")
    
    # 自动刷新
    placeholder = st.empty()
    
    # 刷新按钮
    col_refresh1, col_refresh2, col_refresh3 = st.columns([1, 1, 4])
    with col_refresh1:
        if st.button("🔄 刷新数据", width='stretch'):
            st.session_state.last_refresh = time.time()
            st.rerun()
    with col_refresh2:
        auto_refresh = st.checkbox(
            "自动刷新 (10秒)", 
            value=st.session_state.auto_refresh,
            key='auto_refresh_checkbox'
        )
        # 更新session state
        if auto_refresh != st.session_state.auto_refresh:
            st.session_state.auto_refresh = auto_refresh
            st.session_state.last_refresh = time.time()
    
    # 加载数据
    data = load_trading_data()
    trades_history = load_trades_history()
    
    if data is None:
        st.error("无法加载数据，请检查交易程序是否运行")
        return
    
    # 检查数据文件是否存在
    if data.get('file_not_found'):
        st.warning("""
        ⚠️ **未检测到交易数据文件**
        
        请按以下步骤操作：
        1. 确保已启动交易程序 `deepseekok2.py`
        2. 交易程序启动后会自动创建数据文件
        3. 刷新此页面即可看到实时数据
        
        **启动交易程序：**
        - Windows: 双击 `启动交易程序.bat`
        - Linux/Mac: 运行 `./启动交易程序.sh`
        - 命令行: `python deepseekok2.py`
        """)
        st.info("💡 数据文件路径：`trading_data.json`")
    
    # 状态指示器
    status_color = "🟢" if data['status'] == 'running' else "🔴"
    st.markdown(f"""
    <div class="{'status-card' if data['status'] == 'running' else 'warning-card'}">
        <h2>{status_color} 运行状态: {data['status'].upper()}</h2>
        <p>最后更新: {data['last_update']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 第一行：账户信息和BTC信息
    st.subheader("📊 实时监控")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 可用余额",
            f"{data['account']['balance']:.2f} USDT",
            help="可用于开仓的USDT余额"
        )
    
    with col2:
        st.metric(
            "📈 总权益",
            f"{data['account']['equity']:.2f} USDT",
            help="账户总权益（含未实现盈亏）"
        )
    
    with col3:
        st.metric(
            "⚡ 杠杆倍数",
            f"{data['account']['leverage']}x",
            help="当前使用的杠杆倍数"
        )
    
    with col4:
        change_delta = f"{data['btc']['change']:+.2f}%" if data['btc']['change'] != 0 else "0.00%"
        st.metric(
            "₿ BTC/USDT",
            f"${data['btc']['price']:,.2f}",
            delta=change_delta,
            help="当前BTC价格"
        )
    
    # 第二行：持仓信息和绩效统计
    col5, col6 = st.columns(2)
    
    with col5:
        st.markdown("### 📦 当前持仓")
        if data['position']:
            pos = data['position']
            side_emoji = "🟢" if pos['side'] == 'long' else "🔴"
            pnl_class = "profit" if pos['unrealized_pnl'] >= 0 else "loss"
            side_gradient = "linear-gradient(135deg, #11998e 0%, #38ef7d 100%)" if pos['side'] == 'long' else "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)"
            st.markdown(f"""
            <div class="info-card" style="border-left: 4px solid {'#38ef7d' if pos['side'] == 'long' else '#f5576c'};">
                <p style="font-size: 20px; color: #e0e0e0;"><b>{side_emoji} 方向:</b> <span style="background: {side_gradient}; -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800;">{pos['side'].upper()}</span></p>
                <p style="font-size: 18px; color: #e0e0e0;"><b>📊 数量:</b> {pos['size']:.2f} 张</p>
                <p style="font-size: 18px; color: #e0e0e0;"><b>💵 入场价格:</b> <span class="price-big" style="font-size: 20px;">${pos['entry_price']:,.2f}</span></p>
                <p style="font-size: 18px; color: #e0e0e0;"><b>💰 未实现盈亏:</b> <span class="{pnl_class}" style="font-size: 22px;">{pos['unrealized_pnl']:+.2f} USDT</span></p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="info-card" style="text-align: center;">
                <p style="font-size: 18px; color: #b0b0b0;">📭 当前无持仓</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col6:
        st.markdown("### 📈 绩效统计")
        perf = data['performance']
        pnl_class = "profit" if perf['total_pnl'] >= 0 else "loss"
        win_rate_color = "#38ef7d" if perf['win_rate'] >= 50 else "#f5576c"
        st.markdown(f"""
        <div class="info-card">
            <p style="font-size: 18px; color: #e0e0e0;"><b>💵 总盈亏:</b> <span class="{pnl_class}" style="font-size: 24px;">{perf['total_pnl']:+.2f} USDT</span></p>
            <p style="font-size: 18px; color: #e0e0e0;"><b>🎯 胜率:</b> <span style="color: {win_rate_color}; font-weight: 700; font-size: 20px;">{perf['win_rate']:.1f}%</span></p>
            <p style="font-size: 18px; color: #e0e0e0;"><b>📊 总交易次数:</b> <span style="color: #667eea; font-weight: 700; font-size: 20px;">{perf['total_trades']}</span></p>
        </div>
        """, unsafe_allow_html=True)
    
    # 第三行：账户总权益曲线
    st.markdown("### 📈 账户总权益曲线")
    equity_chart = create_equity_chart()
    st.plotly_chart(
        equity_chart,
        use_container_width=True,
        config={'displayModeBar': True, 'displaylogo': False}
    )
    
    # 第四行：AI决策和信号分布
    col7, col8 = st.columns([2, 1])
    
    with col7:
        st.markdown("### 🤖 AI实时决策")
        ai = data['ai_signal']
        
        # 选择AI卡片样式
        card_class = {
            'BUY': 'ai-card-buy',
            'SELL': 'ai-card-sell',
            'HOLD': 'ai-card-hold'
        }.get(ai['signal'], 'ai-card-hold')
        
        # 信号图标
        signal_icons = {
            'BUY': '📈 ⬆️',
            'SELL': '📉 ⬇️',
            'HOLD': '⏸️ ⏹️'
        }
        signal_icon = signal_icons.get(ai['signal'], '❓')
        
        # 信心徽章颜色
        confidence_badge = {
            'HIGH': '<span style="background: #38ef7d; padding: 5px 15px; border-radius: 20px; font-weight: 800;">🔥 高信心</span>',
            'MEDIUM': '<span style="background: #ffd93d; padding: 5px 15px; border-radius: 20px; font-weight: 800; color: #333;">⚡ 中信心</span>',
            'LOW': '<span style="background: #f5576c; padding: 5px 15px; border-radius: 20px; font-weight: 800;">⚠️ 低信心</span>',
            'N/A': '<span style="background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px; font-weight: 800;">⏳ 待分析</span>'
        }.get(ai['confidence'], '<span>N/A</span>')
        
        st.markdown(f"""
        <div class="{card_class}">
            <h1 style="margin: 0; color: white; font-size: 48px; text-align: center; font-weight: 900; text-shadow: 0 0 20px rgba(255,255,255,0.5);">
                {signal_icon} {ai['signal']}
            </h1>
            <div style="text-align: center; margin: 15px 0;">
                {confidence_badge}
            </div>
            <p style="font-size: 16px; margin: 10px 0; text-align: center; opacity: 0.9;"><b>⏰ 时间:</b> {ai['timestamp']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="info-card">
            <p style="font-size: 17px; margin: 10px 0; color: #e0e0e0; line-height: 1.6;"><b>🎯 分析理由:</b><br>{ai['reason']}</p>
            <hr style="border: none; border-top: 1px solid rgba(102, 126, 234, 0.2); margin: 15px 0;">
            <div style="display: flex; justify-content: space-around;">
                <div style="text-align: center;">
                    <p style="font-size: 14px; color: #b0b0b0; margin: 5px 0;">🛑 止损价</p>
                    <p style="font-size: 22px; color: #f5576c; font-weight: 700; margin: 5px 0;">${ai['stop_loss']:,.2f}</p>
                </div>
                <div style="text-align: center;">
                    <p style="font-size: 14px; color: #b0b0b0; margin: 5px 0;">✅ 止盈价</p>
                    <p style="font-size: 22px; color: #38ef7d; font-weight: 700; margin: 5px 0;">${ai['take_profit']:,.2f}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col8:
        st.markdown("### 📊 信号分布")
        signal_chart = create_signal_distribution_chart(trades_history)
        st.plotly_chart(
            signal_chart,
            use_container_width=True,
            config={'displayModeBar': True, 'displaylogo': False}
        )
    
    # 第五行：交易记录
    st.markdown("### 📝 交易记录")
    if trades_history:
        df_trades = pd.DataFrame(trades_history)
        
        # 格式化数据
        df_trades['timestamp'] = pd.to_datetime(df_trades['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        df_trades['price'] = df_trades['price'].apply(lambda x: f"${x:,.2f}")
        df_trades['amount'] = df_trades['amount'].apply(lambda x: f"{x:.2f}")
        df_trades['pnl'] = df_trades['pnl'].apply(lambda x: f"{x:+.2f}" if x != 0 else "-")
        
        # 只显示需要的列
        display_df = df_trades[['timestamp', 'signal', 'price', 'amount', 'confidence', 'reason']].tail(20)
        display_df.columns = ['时间', '信号', '价格', '数量', '信心', '理由']
        
        # 反转顺序（最新的在上面）
        display_df = display_df.iloc[::-1].reset_index(drop=True)
        
        st.dataframe(
            display_df,
            width='stretch',
            height=400
        )
    else:
        st.info("暂无交易记录")
    
    # 自动刷新逻辑
    if st.session_state.auto_refresh:
        current_time = time.time()
        elapsed = current_time - st.session_state.last_refresh
        
        # 如果距离上次刷新超过10秒，触发刷新
        if elapsed >= 10:
            st.session_state.last_refresh = current_time
            time.sleep(0.1)  # 短暂延迟避免过于频繁
            st.rerun()
        else:
            # 显示倒计时
            remaining = int(10 - elapsed)
            st.info(f"⏳ 下次自动刷新还有 {remaining} 秒...")
            time.sleep(1)  # 等待1秒后重新检查
            st.rerun()

if __name__ == "__main__":
    main()

