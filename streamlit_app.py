"""
Streamlit Trading Dashboard
Yahoo Financeから株価データを取得してチャート表示とバックテスト結果を表示
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import json
import os

from app.data.yahoo import fetch_yahoo_data
from app.models.dfcandle import DataFrameCandle
import constants

# ページ設定
st.set_page_config(
    page_title="Trading Chart - kabucomtrading",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# カスタムCSS（ダークテーマ）
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stButton>button {
        width: 100%;
        background-color: #2962ff;
        color: white;
    }
    .stButton>button:hover {
        background-color: #1e53e5;
    }
    div[data-testid="stMetricValue"] {
        font-size: 20px;
    }
</style>
""", unsafe_allow_html=True)

# タイトル
st.title("📈 Trading Chart - kabucomtrading")

# サイドバー
with st.sidebar:
    st.header("⚙️ 設定")
    
    # データソース選択
    data_source = st.radio(
        "データソース",
        ["Yahoo Finance", "kabusapi"],
        index=0,
        help="データ取得元を選択"
    )
    
    # 銘柄コード入力
    product_code = st.text_input(
        "銘柄コード",
        value="1459",
        help="日本株の証券コード（例: 1459, 7203, 9984）"
    )
    
    # 時間軸選択
    duration = st.selectbox(
        "時間軸",
        ["5s", "1m", "1h"],
        index=1,
        help="ローソク足の時間軸"
    )
    
    # 期間（日数）
    period_days = st.slider(
        "データ取得期間（日）",
        min_value=7,
        max_value=730,
        value=365,
        help="過去何日分のデータを取得するか"
    )
    
    # チャート高さ
    chart_height = st.slider(
        "チャート高さ（px）",
        min_value=300,
        max_value=1200,
        value=600,
        step=50,
        help="チャートの高さを調整"
    )
    
    st.divider()
    
    # データ取得ボタン
    if st.button("📊 チャート更新", type="primary"):
        st.session_state.reload_data = True
    
    # バックテスト結果表示ボタン
    if st.button("🎯 バックテスト結果表示"):
        st.session_state.show_backtest = True

# セッションステート初期化
if 'reload_data' not in st.session_state:
    st.session_state.reload_data = True
if 'show_backtest' not in st.session_state:
    st.session_state.show_backtest = False

# データ取得関数
@st.cache_data(ttl=300)  # 5分間キャッシュ
def load_chart_data(product_code, period_days, duration):
    """Yahoo Financeからデータを取得"""
    duration_time = constants.TRADE_MAP.get(duration, {}).get('duration', constants.DURATION_1M)
    
    yahoo_candles = fetch_yahoo_data(
        product_code=product_code,
        period_days=period_days,
        duration=duration_time,
        market='T'
    )
    
    if not yahoo_candles:
        return None
    
    # DataFrameに変換
    data = []
    for candle in yahoo_candles:
        data.append({
            'time': candle.time,
            'open': candle.open,
            'high': candle.high,
            'low': candle.low,
            'close': candle.close,
            'volume': candle.volume
        })
    
    df = pd.DataFrame(data)
    df['time'] = pd.to_datetime(df['time'])
    return df

# バックテスト結果読み込み
def load_backtest_results():
    """backtest_results.jsonを読み込み"""
    results_file = 'backtest_results.json'
    
    if not os.path.exists(results_file):
        return None
    
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"エラー: {e}")
        return None

# メインエリア
if data_source == "Yahoo Finance":
    # データ取得
    if st.session_state.reload_data:
        with st.spinner('データ取得中...'):
            df = load_chart_data(product_code, period_days, duration)
            st.session_state.reload_data = False
            
            if df is not None:
                st.session_state.chart_data = df
                st.success(f'✅ データ取得成功: {len(df)}件のローソク足データ')
            else:
                st.error('❌ データ取得に失敗しました')
    
    # チャート表示
    if 'chart_data' in st.session_state:
        df = st.session_state.chart_data
        
        # 統計情報表示
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("データ数", f"{len(df)}本")
        with col2:
            st.metric("最新価格", f"{df['close'].iloc[-1]:.2f}")
        with col3:
            change = df['close'].iloc[-1] - df['close'].iloc[0]
            change_pct = (change / df['close'].iloc[0]) * 100
            st.metric("変化", f"{change:.2f}", f"{change_pct:+.2f}%")
        with col4:
            st.metric("最高値", f"{df['high'].max():.2f}")
        
        # ローソク足チャート（Plotly）
        fig = go.Figure(data=[go.Candlestick(
            x=df['time'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350',
            name='OHLC'
        )])
        
        fig.update_layout(
            title=f'{product_code} - {duration}足',
            xaxis_title='時刻',
            yaxis_title='価格',
            height=chart_height,
            template='plotly_dark',
            xaxis_rangeslider_visible=False,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.info('👈 サイドバーの「チャート更新」ボタンをクリックしてデータを取得してください')

else:
    st.warning("kabusapiは現在未実装です。Yahoo Financeをご利用ください。")

# バックテスト結果表示
if st.session_state.show_backtest:
    st.divider()
    st.header("🎯 バックテスト結果")
    
    results = load_backtest_results()
    
    if results:
        # 基本情報
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("銘柄", results['product_code'])
        with col2:
            st.metric("期間", f"{results['period_days']}日")
        with col3:
            st.metric("時間軸", results['duration'])
        with col4:
            timestamp = datetime.fromisoformat(results['timestamp'].replace('Z', '+00:00'))
            st.metric("実行日時", timestamp.strftime('%Y-%m-%d %H:%M'))
        
        # 最適化パラメータ
        if 'results' in results and 'optimized_params' in results['results']:
            st.subheader("📋 最適化パラメータ")
            params = results['results']['optimized_params']
            
            cols = st.columns(3)
            idx = 0
            
            if params.get('ema_enable'):
                with cols[idx % 3]:
                    st.info(f"**✓ EMA**\nPeriod: {params['ema_period_1']}, {params['ema_period_2']}")
                idx += 1
            
            if params.get('bb_enable'):
                with cols[idx % 3]:
                    st.info(f"**✓ Bollinger Bands**\nN={params['bb_n']}, K={params['bb_k']}")
                idx += 1
            
            if params.get('ichimoku_enable'):
                with cols[idx % 3]:
                    st.info("**✓ 一目均衡表**\n有効")
                idx += 1
            
            if params.get('rsi_enable'):
                with cols[idx % 3]:
                    st.info(f"**✓ RSI**\nPeriod={params['rsi_period']}\n買={params['rsi_buy_thread']}, 売={params['rsi_sell_thread']}")
                idx += 1
            
            if params.get('macd_enable'):
                with cols[idx % 3]:
                    st.info(f"**✓ MACD**\nFast={params['macd_fast_period']}, Slow={params['macd_slow_period']}, Signal={params['macd_signal_period']}")
                idx += 1
        
        # パフォーマンス
        if 'results' in results:
            st.subheader("📊 指標別パフォーマンス")
            
            perf_data = []
            res = results['results']
            
            if 'ema' in res:
                perf_data.append({'指標': 'EMA', 'パフォーマンス (%)': res['ema']['performance']})
            if 'bollinger_bands' in res:
                perf_data.append({'指標': 'Bollinger Bands', 'パフォーマンス (%)': res['bollinger_bands']['performance']})
            if 'ichimoku' in res:
                perf_data.append({'指標': '一目均衡表', 'パフォーマンス (%)': res['ichimoku']['performance']})
            if 'rsi' in res:
                perf_data.append({'指標': 'RSI', 'パフォーマンス (%)': res['rsi']['performance']})
            if 'macd' in res:
                perf_data.append({'指標': 'MACD', 'パフォーマンス (%)': res['macd']['performance']})
            
            if perf_data:
                perf_df = pd.DataFrame(perf_data)
                
                # 棒グラフ
                fig_perf = go.Figure(data=[
                    go.Bar(
                        x=perf_df['指標'],
                        y=perf_df['パフォーマンス (%)'],
                        marker_color='#2962ff',
                        text=perf_df['パフォーマンス (%)'],
                        textposition='auto',
                    )
                ])
                
                fig_perf.update_layout(
                    title='各指標のパフォーマンス',
                    xaxis_title='指標',
                    yaxis_title='パフォーマンス (%)',
                    height=400,
                    template='plotly_dark'
                )
                
                st.plotly_chart(fig_perf, use_container_width=True)
                
                # テーブル表示
                st.dataframe(perf_df, use_container_width=True)
    else:
        st.error("バックテスト結果が見つかりません。backtest_yahoo.pyを実行してください。")
    
    if st.button("結果を非表示"):
        st.session_state.show_backtest = False
        st.rerun()

# フッター
st.divider()
st.markdown("""
<div style='text-align: center; color: #888;'>
    <p>kabucomtrading - Trading Dashboard with Yahoo Finance & Backtest Results</p>
</div>
""", unsafe_allow_html=True)
