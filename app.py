import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from binance.um_futures import UMFutures as Client
from datetime import datetime
import time

# --- 配置区 ---
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
PERIOD = '4h' 
WINDOW_SIZE = 42  # 7天平滑窗口 (42 * 4h = 168h = 7 days)

# --- API 密钥集成 ---
# 建议在 Streamlit Secrets 或 环境变量中设置，为了方便你修改，这里预留位置
BINANCE_API_KEY = st.secrets.get("api_key", "")
BINANCE_API_SECRET = st.secrets.get("api_secret", "")

# 初始化客户端 (即便不传入Key，部分公开数据也能获取，但传入Key更稳定)
client = Client(key=BINANCE_API_KEY, secret=BINANCE_API_SECRET)

def get_data(symbol):
    """
    逆向工程核心：通过获取'全球交易者多空账户比例'并进行EMA平滑，
    模拟社区投票器那种反映中线真实意图的缓慢变化过程。
    """
    try:
        # 修正方法名：使用官方接口获取多空账户比
        data = client.global_long_short_accounts(symbol=symbol, period=PERIOD, limit=100)
        
        if not data:
            return 50.0, 50.0, "API 未返回数据"
            
        df = pd.DataFrame(data)
        # 将字符串转为浮点数
        df['longAccount'] = df['longAccount'].astype(float)
        
        # 7天EMA平滑：这是模拟“投票器”缓慢变动的关键
        # 它过滤掉了日内的剧烈波动，保留了中线意图
        df['smoothed_long'] = df['longAccount'].ewm(span=WINDOW_SIZE, adjust=False).mean() * 100
        
        long_pc = round(df['smoothed_long'].iloc[-1], 2)
        short_pc = round(100 - long_pc, 2)
        return long_pc, short_pc, None
    except Exception as e:
        return 50.0, 50.0, str(e)

def create_sentiment_bar(symbol, long_pc, short_pc):
    """创建符合需求的红绿对抗进度条"""
    fig = go.Figure()

    # 看空部分 (红色 - 左侧)
    fig.add_trace(go.Bar(
        y=[symbol], x=[short_pc],
        name='Short',
        orientation='h',
        marker=dict(color='#FF4B4B'),
        text=f"看空 {short_pc}%",
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=14, color='white'),
        hoverinfo='none'
    ))

    # 看多部分 (绿色 - 右侧)
    fig.add_trace(go.Bar(
        y=[symbol], x=[long_pc],
        name='Long',
        orientation='h',
        marker=dict(color='#00CC96'),
        text=f"看多 {long_pc}%",
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(size=14, color='white'),
        hoverinfo='none'
    ))

    fig.update_layout(
        barmode='stack',
        xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]),
        yaxis=dict(showgrid=False, tickfont=dict(size=18, color='white', family="Arial Black")),
        showlegend=False,
        height=70,
        margin=dict(l=10, r=10, t=5, b=5),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig

# --- 网页布局 ---
st.set_page_config(page_title="中线多空对抗指标", layout="wide")

# CSS 强制深色风格
st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    [data-testid="stMetricValue"] { font-size: 25px; }
    h3 { margin-bottom: 0rem; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 币安中线情绪对抗动态图")
st.caption(f"模拟社区投票器逻辑 (7天EMA平滑) | 数据源: Binance Global Account Ratio")

placeholder = st.empty()

# 渲染循环
while True:
    with placeholder.container():
        st.write(f"最后刷新时间: {datetime.now().strftime('%H:%M:%S')}")
        
        for symbol in SYMBOLS:
            long_v, short_v, error = get_data(symbol)
            
            with st.container():
                col_text, col_bar = st.columns([1, 5])
                with col_text:
                    st.markdown(f"### {symbol[:3]}")
                    if error:
                        st.error("接口异常")
                    elif long_v >= 65:
                        st.warning("🔴 极度看多(反向预警)")
                    elif long_v <= 35:
                        st.success("🟢 极度看空(反向预警)")
                
                with col_bar:
                    # 使用 time.time() 确保 ID 唯一，修复 DuplicateElementId 报错
                    unique_key = f"chart_{symbol}_{time.time()}"
                    st.plotly_chart(
                        create_sentiment_bar(symbol, long_v, short_v), 
                        use_container_width=True, 
                        config={'displayModeBar': False},
                        key=unique_key
                    )
            st.write("") 

        time.sleep(10) # 建议频率不宜过快，防止被币安封禁IP