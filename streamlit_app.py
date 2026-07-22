"""
Streamlit Trading Dashboard
Yahoo Financeから株価データを取得してチャート表示・比較・財務情報を確認する
"""

import json
import os
import shutil
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
import numpy as np

import constants
import settings
from app.data.yahoo import fetch_yahoo_data, save_yahoo_data_to_db
from app.models.dfcandle import DataFrameCandle

# 拡張バックテスト機能をインポート（オプション）
try:
    from backtest_metrics import BacktestMetrics
    from backtest_visualizer import BacktestVisualizer
    from trade_logger import TradeLogger
    ENHANCED_BACKTEST_AVAILABLE = True
except ImportError:
    ENHANCED_BACKTEST_AVAILABLE = False

# CSVキャッシュディレクトリ
CACHE_DIR = settings.cache_dir
BACKTEST_RESULTS_FILE = settings.backtest_results_file
BACKTEST_DETAILS_DIR = settings.backtest_details_dir
os.makedirs(CACHE_DIR, exist_ok=True)

# streamlit_appではバックテスト機能を無効化し、strategy_labへ統合する
BACKTEST_ENABLED = False

# ページ設定
st.set_page_config(
    page_title="Trading Chart - kabucomtrading",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
# カスタムCSS（ダークテーマ）
st.markdown(
    """
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
    .success-box {
        padding: 1rem;
        background-color: #1e3a1e;
        border-left: 4px solid #26a69a;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        background-color: #3a2e1e;
        border-left: 4px solid #ff9800;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

# タイトル
st.title("📈 Trading Chart - kabucomtrading")

# サイドバー
with st.sidebar:
    st.header("⚙️ 設定")

    # タブで機能を分ける
    tab1, tab2, tab3, tab4 = st.tabs(["📊 チャート", "🧪 Strategy Lab", "📉 比較", "📋 財務情報"])

    with tab1:
        st.subheader("チャート設定")

        # データソース選択
        data_source = st.radio("データソース", ["Yahoo Finance", "kabusapi"], index=0, help="データ取得元を選択")

        # 銘柄コード入力
        product_code = st.text_input("銘柄コード", value="7203", help="日本株の証券コード（例: 7203, 1459, 9984）")

        # 時間軸選択
        duration = st.selectbox(
            "時間軸",
            ["5s", "1m", "1h", "1d"],
            index=3,  # デフォルトを1dに設定
            help="ローソク足の時間軸",
        )

        # 期間（日数）
        period_days = st.slider(
            "データ取得期間（日）",
            min_value=7,
            max_value=3650,  # 最大10年分
            value=3650,  # デフォルトを最大10年に設定
            help="過去何日分のデータを取得するか（日足推奨: 最大10年）",
        )

        # チャート高さ
        chart_height = st.slider(
            "チャート高さ（px）", min_value=300, max_value=1200, value=600, step=50, help="チャートの高さを調整"
        )

        st.divider()

        # テクニカル指標設定
        st.subheader("テクニカル指標")

        show_sma = st.checkbox("SMA（単純移動平均）", value=False)
        if show_sma:
            sma_periods = st.multiselect("SMA期間", [5, 7, 14, 21, 50, 100, 200], default=[7, 14, 50])

        show_ema = st.checkbox("EMA（指数移動平均）", value=False)
        if show_ema:
            ema_periods = st.multiselect("EMA期間", [5, 7, 12, 14, 26, 50, 100], default=[12, 26])

        show_bbands = st.checkbox("Bollinger Bands", value=False)
        if show_bbands:
            bb_period = st.slider("期間", 5, 50, 20)
            bb_std = st.slider("標準偏差", 1.0, 3.0, 2.0, 0.1)

        show_volume = st.checkbox("出来高", value=True)

        st.divider()

        # キャッシュ設定
        force_refresh = st.checkbox(
            "強制更新（キャッシュを使わない）", value=False, help="チェックするとAPIから最新データを取得します"
        )

        # データ取得ボタン
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("📊 チャート更新", type="primary"):
                st.session_state.reload_data = True
                st.session_state.force_refresh = force_refresh
        with col2:
            if st.button("🗑️ キャッシュクリア"):
                import shutil

                if os.path.exists(CACHE_DIR):
                    shutil.rmtree(CACHE_DIR)
                    os.makedirs(CACHE_DIR)
                    st.success("キャッシュを削除しました")

    with tab2:
        st.subheader("戦略検証は Strategy Lab へ統合")
        st.info("この画面ではバックテストを提供しません。戦略作成・最適化は strategy_lab.py を使用してください。")
        st.code("uv run streamlit run strategy_lab.py", language="bash")
        st.caption("既存のチャート確認・比較・財務情報はこの streamlit_app.py で引き続き利用できます。")

    with tab3:
        st.subheader("銘柄比較")

        compare_codes = st.text_area(
            "比較する銘柄（1行に1つ）", value="7203\n1459\n9984", height=100, help="改行区切りで複数の銘柄コードを入力"
        )

        compare_period = st.slider(
            "比較期間（日）",
            min_value=7,
            max_value=3650,  # 最大10年分
            value=3650,  # デフォルトを最大10年に設定
            key="compare_period",
            help="複数銘柄を比較する期間（日足推奨: 最大10年）",
        )

        compare_duration = st.selectbox("比較時間軸", ["1m", "1h", "1d"], index=2, key="compare_duration")

        normalize = st.checkbox("正規化表示", value=True, help="開始時点を100として正規化")

        st.divider()

        if st.button("📊 比較実行", type="primary"):
            st.session_state.run_compare = True

    # 財務情報タブ
    with tab4:
        st.subheader("財務情報取得")

        col1, col2 = st.columns([3, 1])
        with col1:
            fin_code = st.text_input("銘柄コード", value="7203", key="fin_code", help="財務情報を取得する銘柄コード")
        with col2:
            fin_market = st.selectbox("市場", ["T", ""], index=0, key="fin_market", help="T=東証, 空白=米国株")

        if st.button("📋 財務情報を取得", key="fetch_financials"):
            with st.spinner("財務情報を取得中..."):
                try:
                    import yfinance as yf

                    # ティッカーシンボル作成
                    ticker_symbol = f"{fin_code}.{fin_market}" if fin_market else fin_code
                    ticker = yf.Ticker(ticker_symbol)

                    # デバッグ情報
                    with st.expander("🔍 データ取得状況", expanded=False):
                        st.write(f"ティッカーシンボル: {ticker_symbol}")
                        st.write("データ取得を試行中...")

                    # 基本情報
                    st.subheader(f"📊 {ticker_symbol} - 企業情報")

                    try:
                        info = ticker.info

                        # デバッグ: infoのキーを表示
                        with st.expander("🔍 取得されたデータキー", expanded=False):
                            st.write(f"info keys: {list(info.keys())[:20]}...")  # 最初の20個

                        # 企業情報を列で表示
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("企業名", info.get("longName", "N/A"))
                            st.metric("セクター", info.get("sector", "N/A"))
                            st.metric("業種", info.get("industry", "N/A"))

                        with col2:
                            market_cap = info.get("marketCap", 0)
                            if market_cap:
                                st.metric("時価総額", f"¥{market_cap:,.0f}")
                            else:
                                st.metric("時価総額", "N/A")

                            employees = info.get("fullTimeEmployees", "N/A")
                            st.metric("従業員数", f"{employees:,}" if isinstance(employees, int) else employees)

                            st.metric("国", info.get("country", "N/A"))

                        with col3:
                            current_price = info.get("currentPrice", info.get("regularMarketPrice", 0))
                            if current_price:
                                st.metric("株価", f"¥{current_price:,.2f}")
                            else:
                                st.metric("株価", "N/A")

                            pe_ratio = info.get("trailingPE", "N/A")
                            if pe_ratio and pe_ratio != "N/A":
                                st.metric("PER", f"{pe_ratio:.2f}")
                            else:
                                st.metric("PER", "N/A")

                            pb_ratio = info.get("priceToBook", "N/A")
                            if pb_ratio and pb_ratio != "N/A":
                                st.metric("PBR", f"{pb_ratio:.2f}")
                            else:
                                st.metric("PBR", "N/A")

                        # 事業内容
                        if "longBusinessSummary" in info:
                            with st.expander("📝 事業内容"):
                                st.write(info["longBusinessSummary"])

                    except Exception as e:
                        st.warning(f"企業情報の取得に失敗しました: {e!s}")

                    # 財務諸表タブ
                    fin_tab1, fin_tab2, fin_tab3, fin_tab4, fin_tab5 = st.tabs(
                        ["📊 損益計算書", "💰 貸借対照表", "💵 キャッシュフロー", "📈 主要指標", "📉 財務グラフ"]
                    )

                    # 損益計算書
                    with fin_tab1:
                        st.subheader("損益計算書 (Income Statement)")
                        try:
                            # 年次と四半期の両方を取得
                            income_stmt_annual = ticker.financials
                            income_stmt_quarterly = ticker.quarterly_financials

                            # デバッグ情報
                            with st.expander("🔍 データ構造確認", expanded=False):
                                st.write(
                                    f"年次データのshape: {income_stmt_annual.shape if not income_stmt_annual.empty else 'Empty'}"
                                )
                                st.write(
                                    f"四半期データのshape: {income_stmt_quarterly.shape if not income_stmt_quarterly.empty else 'Empty'}"
                                )
                                if not income_stmt_annual.empty:
                                    st.write(f"年次データの項目数: {len(income_stmt_annual.index)}")
                                    st.write(f"年次データの期間: {list(income_stmt_annual.columns)}")

                            if not income_stmt_annual.empty:
                                st.write("**年次データ:**")
                                st.dataframe(income_stmt_annual.style.format("{:,.0f}"), width="stretch")

                                # CSVダウンロード
                                csv = income_stmt_annual.to_csv().encode("utf-8-sig")
                                st.download_button(
                                    label="📥 年次損益計算書をCSVダウンロード",
                                    data=csv,
                                    file_name=f"{ticker_symbol}_income_statement_annual.csv",
                                    mime="text/csv",
                                    key="income_annual_csv",
                                )
                            else:
                                st.info("年次損益計算書データが取得できませんでした")

                            if not income_stmt_quarterly.empty:
                                st.write("**四半期データ:**")
                                st.dataframe(income_stmt_quarterly.style.format("{:,.0f}"), width="stretch")

                                csv = income_stmt_quarterly.to_csv().encode("utf-8-sig")
                                st.download_button(
                                    label="📥 四半期損益計算書をCSVダウンロード",
                                    data=csv,
                                    file_name=f"{ticker_symbol}_income_statement_quarterly.csv",
                                    mime="text/csv",
                                    key="income_quarterly_csv",
                                )

                            if income_stmt_annual.empty and income_stmt_quarterly.empty:
                                st.warning(
                                    "損益計算書データが利用できません。この銘柄は財務諸表データを提供していない可能性があります。"
                                )

                        except Exception as e:
                            st.error(f"損益計算書の取得エラー: {e!s}")
                            st.info("データ取得に失敗しました。別の銘柄を試すか、後でもう一度お試しください。")

                    # 貸借対照表
                    with fin_tab2:
                        st.subheader("貸借対照表 (Balance Sheet)")
                        try:
                            balance_sheet_annual = ticker.balance_sheet
                            balance_sheet_quarterly = ticker.quarterly_balance_sheet

                            if not balance_sheet_annual.empty:
                                st.write("**年次データ:**")
                                st.dataframe(balance_sheet_annual.style.format("{:,.0f}"), width="stretch")

                                # CSV ダウンロード
                                csv = balance_sheet_annual.to_csv().encode("utf-8-sig")
                                st.download_button(
                                    label="📥 年次貸借対照表をCSVダウンロード",
                                    data=csv,
                                    file_name=f"{ticker_symbol}_balance_sheet_annual.csv",
                                    mime="text/csv",
                                    key="balance_annual_csv",
                                )
                            else:
                                st.info("年次貸借対照表データが取得できませんでした")

                            if not balance_sheet_quarterly.empty:
                                st.write("**四半期データ:**")
                                st.dataframe(balance_sheet_quarterly.style.format("{:,.0f}"), width="stretch")

                                csv = balance_sheet_quarterly.to_csv().encode("utf-8-sig")
                                st.download_button(
                                    label="📥 四半期貸借対照表をCSVダウンロード",
                                    data=csv,
                                    file_name=f"{ticker_symbol}_balance_sheet_quarterly.csv",
                                    mime="text/csv",
                                    key="balance_quarterly_csv",
                                )

                            if balance_sheet_annual.empty and balance_sheet_quarterly.empty:
                                st.warning(
                                    "貸借対照表データが利用できません。この銘柄は財務諸表データを提供していない可能性があります。"
                                )

                        except Exception as e:
                            st.error(f"貸借対照表の取得エラー: {e!s}")
                            st.info("データ取得に失敗しました。別の銘柄を試すか、後でもう一度お試しください。")

                    # キャッシュフロー
                    with fin_tab3:
                        st.subheader("キャッシュフロー計算書 (Cash Flow)")
                        try:
                            cash_flow_annual = ticker.cashflow
                            cash_flow_quarterly = ticker.quarterly_cashflow

                            if not cash_flow_annual.empty:
                                st.write("**年次データ:**")
                                st.dataframe(cash_flow_annual.style.format("{:,.0f}"), width="stretch")

                                # CSV ダウンロード
                                csv = cash_flow_annual.to_csv().encode("utf-8-sig")
                                st.download_button(
                                    label="📥 年次キャッシュフローをCSVダウンロード",
                                    data=csv,
                                    file_name=f"{ticker_symbol}_cash_flow_annual.csv",
                                    mime="text/csv",
                                    key="cashflow_annual_csv",
                                )
                            else:
                                st.info("年次キャッシュフローデータが取得できませんでした")

                            if not cash_flow_quarterly.empty:
                                st.write("**四半期データ:**")
                                st.dataframe(cash_flow_quarterly.style.format("{:,.0f}"), width="stretch")

                                csv = cash_flow_quarterly.to_csv().encode("utf-8-sig")
                                st.download_button(
                                    label="📥 四半期キャッシュフローをCSVダウンロード",
                                    data=csv,
                                    file_name=f"{ticker_symbol}_cash_flow_quarterly.csv",
                                    mime="text/csv",
                                    key="cashflow_quarterly_csv",
                                )

                            if cash_flow_annual.empty and cash_flow_quarterly.empty:
                                st.warning(
                                    "キャッシュフローデータが利用できません。この銘柄は財務諸表データを提供していない可能性があります。"
                                )

                        except Exception as e:
                            st.error(f"キャッシュフローの取得エラー: {e!s}")
                            st.info("データ取得に失敗しました。別の銘柄を試すか、後でもう一度お試しください。")

                    # 主要指標
                    with fin_tab4:
                        st.subheader("主要財務指標")
                        try:
                            # 配当情報
                            st.write("### 配当情報")
                            div_col1, div_col2, div_col3 = st.columns(3)

                            with div_col1:
                                div_yield = info.get("dividendYield", 0)
                                if div_yield:
                                    st.metric("配当利回り", f"{div_yield*100:.2f}%")
                                else:
                                    st.metric("配当利回り", "N/A")

                            with div_col2:
                                div_rate = info.get("dividendRate", "N/A")
                                if div_rate != "N/A":
                                    st.metric("年間配当", f"¥{div_rate:.2f}")
                                else:
                                    st.metric("年間配当", "N/A")

                            with div_col3:
                                payout_ratio = info.get("payoutRatio", "N/A")
                                if payout_ratio and payout_ratio != "N/A":
                                    st.metric("配当性向", f"{payout_ratio*100:.2f}%")
                                else:
                                    st.metric("配当性向", "N/A")

                            # 収益性指標
                            st.write("### 収益性指標")
                            prof_col1, prof_col2, prof_col3 = st.columns(3)

                            with prof_col1:
                                roe = info.get("returnOnEquity", "N/A")
                                if roe and roe != "N/A":
                                    st.metric("ROE", f"{roe*100:.2f}%")
                                else:
                                    st.metric("ROE", "N/A")

                            with prof_col2:
                                roa = info.get("returnOnAssets", "N/A")
                                if roa and roa != "N/A":
                                    st.metric("ROA", f"{roa*100:.2f}%")
                                else:
                                    st.metric("ROA", "N/A")

                            with prof_col3:
                                profit_margin = info.get("profitMargins", "N/A")
                                if profit_margin and profit_margin != "N/A":
                                    st.metric("利益率", f"{profit_margin*100:.2f}%")
                                else:
                                    st.metric("利益率", "N/A")

                            # 成長性指標
                            st.write("### 成長性指標")
                            growth_col1, growth_col2, growth_col3 = st.columns(3)

                            with growth_col1:
                                revenue_growth = info.get("revenueGrowth", "N/A")
                                if revenue_growth and revenue_growth != "N/A":
                                    st.metric("売上成長率", f"{revenue_growth*100:.2f}%")
                                else:
                                    st.metric("売上成長率", "N/A")

                            with growth_col2:
                                earnings_growth = info.get("earningsGrowth", "N/A")
                                if earnings_growth and earnings_growth != "N/A":
                                    st.metric("利益成長率", f"{earnings_growth*100:.2f}%")
                                else:
                                    st.metric("利益成長率", "N/A")

                            with growth_col3:
                                earnings_quarterly_growth = info.get("earningsQuarterlyGrowth", "N/A")
                                if earnings_quarterly_growth and earnings_quarterly_growth != "N/A":
                                    st.metric("四半期利益成長率", f"{earnings_quarterly_growth*100:.2f}%")
                                else:
                                    st.metric("四半期利益成長率", "N/A")

                            # 財務健全性
                            st.write("### 財務健全性")
                            health_col1, health_col2, health_col3 = st.columns(3)

                            with health_col1:
                                debt_to_equity = info.get("debtToEquity", "N/A")
                                if debt_to_equity and debt_to_equity != "N/A":
                                    st.metric("負債資本倍率", f"{debt_to_equity:.2f}")
                                else:
                                    st.metric("負債資本倍率", "N/A")

                            with health_col2:
                                current_ratio = info.get("currentRatio", "N/A")
                                if current_ratio and current_ratio != "N/A":
                                    st.metric("流動比率", f"{current_ratio:.2f}")
                                else:
                                    st.metric("流動比率", "N/A")

                            with health_col3:
                                quick_ratio = info.get("quickRatio", "N/A")
                                if quick_ratio and quick_ratio != "N/A":
                                    st.metric("当座比率", f"{quick_ratio:.2f}")
                                else:
                                    st.metric("当座比率", "N/A")

                        except Exception as e:
                            st.error(f"主要指標の取得エラー: {e!s}")

                    # 財務グラフタブ
                    with fin_tab5:
                        st.subheader("財務データの推移")

                        try:
                            # データの取得
                            income_annual = ticker.financials
                            balance_annual = ticker.balance_sheet
                            cashflow_annual = ticker.cashflow

                            # 売上・利益の推移グラフ
                            if not income_annual.empty:
                                st.write("### 📈 売上・利益の推移")

                                # 主要な収益指標を抽出
                                revenue_items = ["Total Revenue", "Gross Profit", "Operating Income", "Net Income"]
                                available_items = [item for item in revenue_items if item in income_annual.index]

                                if available_items:
                                    fig_revenue = go.Figure()

                                    for item in available_items:
                                        values = income_annual.loc[item].values
                                        dates = income_annual.columns

                                        fig_revenue.add_trace(
                                            go.Scatter(
                                                x=dates,
                                                y=values,
                                                mode="lines+markers",
                                                name=item,
                                                line=dict(width=2),
                                                marker=dict(size=8),
                                            )
                                        )

                                    fig_revenue.update_layout(
                                        title="損益計算書の推移",
                                        xaxis_title="年度",
                                        yaxis_title="金額",
                                        hovermode="x unified",
                                        height=400,
                                    )
                                    st.plotly_chart(fig_revenue, width="stretch")
                                else:
                                    st.info("売上・利益データが見つかりませんでした")

                            # 資産・負債の推移グラフ
                            if not balance_annual.empty:
                                st.write("### 💰 資産・負債の推移")

                                balance_items = [
                                    "Total Assets",
                                    "Total Liabilities Net Minority Interest",
                                    "Stockholders Equity",
                                ]
                                available_balance = [item for item in balance_items if item in balance_annual.index]

                                if available_balance:
                                    fig_balance = go.Figure()

                                    for item in available_balance:
                                        values = balance_annual.loc[item].values
                                        dates = balance_annual.columns

                                        fig_balance.add_trace(
                                            go.Scatter(
                                                x=dates,
                                                y=values,
                                                mode="lines+markers",
                                                name=item,
                                                line=dict(width=2),
                                                marker=dict(size=8),
                                            )
                                        )

                                    fig_balance.update_layout(
                                        title="貸借対照表の推移",
                                        xaxis_title="年度",
                                        yaxis_title="金額",
                                        hovermode="x unified",
                                        height=400,
                                    )
                                    st.plotly_chart(fig_balance, width="stretch")
                                else:
                                    st.info("資産・負債データが見つかりませんでした")

                            # キャッシュフローの推移グラフ
                            if not cashflow_annual.empty:
                                st.write("### 💵 キャッシュフローの推移")

                                cf_items = [
                                    "Operating Cash Flow",
                                    "Investing Cash Flow",
                                    "Financing Cash Flow",
                                    "Free Cash Flow",
                                ]
                                available_cf = [item for item in cf_items if item in cashflow_annual.index]

                                if available_cf:
                                    fig_cf = go.Figure()

                                    for item in available_cf:
                                        values = cashflow_annual.loc[item].values
                                        dates = cashflow_annual.columns

                                        fig_cf.add_trace(
                                            go.Scatter(
                                                x=dates,
                                                y=values,
                                                mode="lines+markers",
                                                name=item,
                                                line=dict(width=2),
                                                marker=dict(size=8),
                                            )
                                        )

                                    fig_cf.update_layout(
                                        title="キャッシュフローの推移",
                                        xaxis_title="年度",
                                        yaxis_title="金額",
                                        hovermode="x unified",
                                        height=400,
                                    )
                                    st.plotly_chart(fig_cf, width="stretch")
                                else:
                                    st.info("キャッシュフローデータが見つかりませんでした")

                            # 利益率の推移
                            if not income_annual.empty:
                                st.write("### 📊 収益性指標の推移")

                                # 利益率を計算
                                if "Total Revenue" in income_annual.index and "Net Income" in income_annual.index:
                                    revenue = income_annual.loc["Total Revenue"]
                                    net_income = income_annual.loc["Net Income"]
                                    profit_margin = (net_income / revenue * 100).dropna()

                                    if not profit_margin.empty:
                                        fig_margin = go.Figure()

                                        fig_margin.add_trace(
                                            go.Bar(
                                                x=profit_margin.index,
                                                y=profit_margin.values,
                                                name="純利益率 (%)",
                                                marker_color="lightblue",
                                            )
                                        )

                                        fig_margin.update_layout(
                                            title="純利益率の推移",
                                            xaxis_title="年度",
                                            yaxis_title="純利益率 (%)",
                                            height=300,
                                        )
                                        st.plotly_chart(fig_margin, width="stretch")

                        except Exception as e:
                            st.error(f"グラフ生成エラー: {e!s}")
                            st.info("データ構造が想定と異なる可能性があります")

                    st.success(f"✅ {ticker_symbol} の財務情報を取得しました")

                except Exception as e:
                    st.error(f"エラーが発生しました: {e!s}")
                    st.info("銘柄コードが正しいか、データが利用可能か確認してください")

# セッションステート初期化
if "reload_data" not in st.session_state:
    st.session_state.reload_data = True
if "show_backtest" not in st.session_state:
    st.session_state.show_backtest = False
if "run_backtest" not in st.session_state:
    st.session_state.run_backtest = False
if "run_compare" not in st.session_state:
    st.session_state.run_compare = False
if "show_enhanced" not in st.session_state:
    st.session_state.show_enhanced = False

if not BACKTEST_ENABLED:
    st.session_state.show_backtest = False
    st.session_state.run_backtest = False
    st.session_state.show_enhanced = False


# CSVキャッシュ関連の関数
def get_cache_filename(product_code, period_days, duration):
    """CSVキャッシュのファイル名を生成"""
    return os.path.join(CACHE_DIR, f"{product_code}_{duration}_{period_days}days.csv")


# 業界平均データの読み込み
@st.cache_data
def load_industry_averages():
    """業界平均PER/PBRデータをExcelファイルから読み込み"""
    try:
        excel_path = "data/perpbr/perpbr202510.xlsx"
        if not os.path.exists(excel_path):
            return None

        # skiprows=2でヘッダーを正しく読み込む
        df = pd.read_excel(excel_path, sheet_name="規模別・業種別（連結）", skiprows=2)

        # プライム市場のデータのみ抽出
        prime_df = df[df["市場区分名"] == "プライム市場"].copy()

        # 業種マッピング辞書を作成
        industry_dict = {}
        for _, row in prime_df.iterrows():
            industry_name = str(row.get("種別", ""))
            if not industry_name or industry_name == "nan" or "総合" in industry_name or "製造業" in industry_name:
                continue

            # 業種名から番号と日本語名を抽出
            industry_key = industry_name.strip()

            industry_dict[industry_key] = {
                "per": row.get("単純＿PER（倍）", None),
                "pbr": row.get("単純＿PBR（倍）", None),
                "companies": row.get("会社数", 0),
            }

        return industry_dict
    except Exception as e:
        st.warning(f"業界平均データ読み込みエラー: {e!s}")
        return None


@st.cache_data
def load_market_cap_by_sector():
    """業種別時価総額データをPDFから読み込み"""
    try:
        import pdfplumber

        pdf_path = "data/marketcapitalizationbyindustrysector/202510.pdf"
        if not os.path.exists(pdf_path):
            return None

        sector_market_cap = {}

        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text()

            # テキストを行ごとに分割
            lines = text.split("\n")

            # データ行を探す（日本語業種名を含む行）
            sector_names = [
                "水産・農林業",
                "鉱業",
                "建設業",
                "食料品",
                "繊維製品",
                "パルプ・紙",
                "化学",
                "医薬品",
                "石油・石炭製品",
                "ゴム製品",
                "ガラス・土石製品",
                "鉄鋼",
                "非鉄金属",
                "金属製品",
                "機械",
                "電気機器",
                "輸送用機器",
                "精密機器",
                "その他製品",
                "電気・ガス業",
                "陸運業",
                "海運業",
                "空運業",
                "倉庫・運輸関連業",
                "情報・通信業",
                "卸売業",
                "小売業",
                "銀行業",
                "証券、商品先物取引業",
                "保険業",
                "その他金融業",
                "不動産業",
                "サービス業",
            ]

            for line in lines:
                for sector in sector_names:
                    if sector in line:
                        # 数字を抽出（時価総額は百万円単位）
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if sector in part and i + 2 < len(parts):
                                try:
                                    # 会社数
                                    companies = int(parts[i + 1].replace(",", ""))
                                    # 時価総額（百万円）
                                    market_cap = int(parts[i + 2].replace(",", ""))

                                    sector_market_cap[sector] = {
                                        "companies": companies,
                                        "market_cap_million": market_cap,
                                        "market_cap_billion": market_cap / 1000,  # 億円
                                        "market_cap_trillion": market_cap / 1000000,  # 兆円
                                    }
                                    break
                                except (ValueError, IndexError):
                                    continue

        return sector_market_cap if sector_market_cap else None
    except Exception as e:
        st.warning(f"時価総額データ読み込みエラー: {e!s}")
        return None


@st.cache_data
def load_top_companies_by_market_cap():
    """時価総額上位企業データをPDFから読み込み"""
    try:
        import pdfplumber

        pdf_path = "data/stocksbymarketcapitalization/202510_r.pdf"
        if not os.path.exists(pdf_path):
            return None

        companies = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                lines = text.split("\n")

                for line in lines:
                    # ランキング行を探す（数字で始まる行）
                    parts = line.split()
                    if len(parts) >= 4 and parts[0].isdigit():
                        try:
                            rank = int(parts[0])
                            code = parts[1]

                            # 銘柄名を抽出（日本語部分）
                            # 時価額は最後の数字
                            market_cap_str = parts[-1].replace(",", "")
                            market_cap = int(market_cap_str)  # 億円

                            # 銘柄名は2番目から最後の数字の前まで
                            name_parts = []
                            for i in range(2, len(parts) - 1):
                                # 英語名は除外（全て大文字またはCapitalized）
                                if not parts[i].isupper() and not all(
                                    c.isupper() or c in ".,()-" for c in parts[i]
                                ):
                                    name_parts.append(parts[i])

                            name = " ".join(name_parts) if name_parts else parts[2]

                            companies.append(
                                {
                                    "rank": rank,
                                    "code": code,
                                    "name": name,
                                    "market_cap_billion": market_cap,
                                    "market_cap_trillion": market_cap / 10000,
                                }
                            )
                        except (ValueError, IndexError):
                            continue

        return companies if companies else None
    except Exception as e:
        st.warning(f"時価総額ランキングデータ読み込みエラー: {e!s}")
        return None


# yfinanceのsector/industryから日本の業種区分へのマッピング
SECTOR_TO_INDUSTRY_MAP = {
    # Consumer Cyclical
    "Consumer Cyclical": "15 機械",  # デフォルト
    "Auto Manufacturers": "16 電気機器",
    "Auto Parts": "17 輸送用機器",
    "Furnishings, Fixtures & Appliances": "15 機械",
    "Residential Construction": "3 建設業",
    "Textile Manufacturing": "5 繊維製品",
    "Apparel Manufacturing": "5 繊維製品",
    "Footwear & Accessories": "5 繊維製品",
    "Packaging & Containers": "6 パルプ・紙",
    "Personal Services": "28 サービス業",
    "Restaurants": "28 サービス業",
    "Apparel Retail": "27 小売業",
    "Department Stores": "27 小売業",
    "Home Improvement Retail": "27 小売業",
    "Luxury Goods": "27 小売業",
    "Internet Retail": "26 情報・通信業",
    "Specialty Retail": "27 小売業",
    "Gambling": "28 サービス業",
    "Leisure": "28 サービス業",
    "Lodging": "28 サービス業",
    "Resorts & Casinos": "28 サービス業",
    "Travel Services": "28 サービス業",
    # Technology
    "Technology": "26 情報・通信業",
    "Consumer Electronics": "16 電気機器",
    "Computer Hardware": "16 電気機器",
    "Electronic Components": "16 電気機器",
    "Electronics & Computer Distribution": "27 小売業",
    "Information Technology Services": "26 情報・通信業",
    "Software—Application": "26 情報・通信業",
    "Software—Infrastructure": "26 情報・通信業",
    "Communication Equipment": "16 電気機器",
    "Semiconductors": "16 電気機器",
    "Semiconductor Equipment & Materials": "16 電気機器",
    "Scientific & Technical Instruments": "15 機械",
    "Solar": "16 電気機器",
    # Financial Services
    "Financial Services": "25 銀行業",
    "Banks—Regional": "25 銀行業",
    "Banks—Diversified": "25 銀行業",
    "Mortgage Finance": "25 銀行業",
    "Capital Markets": "24 証券、商品先物取引業",
    "Financial Data & Stock Exchanges": "24 証券、商品先物取引業",
    "Insurance—Life": "23 保険業",
    "Insurance—Property & Casualty": "23 保険業",
    "Insurance—Diversified": "23 保険業",
    "Insurance—Specialty": "23 保険業",
    "Insurance Brokers": "23 保険業",
    "Asset Management": "24 証券、商品先物取引業",
    "Credit Services": "25 銀行業",
    "Shell Companies": "28 サービス業",
    # Healthcare
    "Healthcare": "8 医薬品",
    "Biotechnology": "8 医薬品",
    "Drug Manufacturers—General": "8 医薬品",
    "Drug Manufacturers—Specialty & Generic": "8 医薬品",
    "Healthcare Plans": "23 保険業",
    "Medical Care Facilities": "28 サービス業",
    "Pharmaceutical Retailers": "27 小売業",
    "Health Information Services": "26 情報・通信業",
    "Medical Devices": "15 機械",
    "Medical Instruments & Supplies": "15 機械",
    "Diagnostics & Research": "8 医薬品",
    "Medical Distribution": "27 小売業",
    # Communication Services
    "Communication Services": "26 情報・通信業",
    "Advertising Agencies": "28 サービス業",
    "Publishing": "26 情報・通信業",
    "Broadcasting": "26 情報・通信業",
    "Entertainment": "26 情報・通信業",
    "Internet Content & Information": "26 情報・通信業",
    "Electronic Gaming & Multimedia": "26 情報・通信業",
    "Telecom Services": "26 情報・通信業",
    # Energy
    "Energy": "9 石油・石炭製品",
    "Oil & Gas E&P": "2 鉱業",
    "Oil & Gas Equipment & Services": "15 機械",
    "Oil & Gas Integrated": "9 石油・石炭製品",
    "Oil & Gas Midstream": "9 石油・石炭製品",
    "Oil & Gas Refining & Marketing": "9 石油・石炭製品",
    "Thermal Coal": "2 鉱業",
    "Uranium": "2 鉱業",
    # Industrials
    "Industrials": "15 機械",
    "Aerospace & Defense": "17 輸送用機器",
    "Airlines": "21 空運業",
    "Airports & Air Services": "21 空運業",
    "Building Products & Equipment": "11 ガラス・土石製品",
    "Farm & Heavy Construction Machinery": "15 機械",
    "Industrial Distribution": "27 小売業",
    "Business Equipment & Supplies": "27 小売業",
    "Conglomerates": "28 サービス業",
    "Consulting Services": "28 サービス業",
    "Electrical Equipment & Parts": "16 電気機器",
    "Engineering & Construction": "3 建設業",
    "Farm Products": "1 水産・農林業",
    "Industrial Products": "15 機械",
    "Metal Fabrication": "14 金属製品",
    "Pollution & Treatment Controls": "15 機械",
    "Railroads": "19 陸運業",
    "Rental & Leasing Services": "28 サービス業",
    "Security & Protection Services": "28 サービス業",
    "Specialty Business Services": "28 サービス業",
    "Specialty Industrial Machinery": "15 機械",
    "Staffing & Employment Services": "28 サービス業",
    "Tools & Accessories": "14 金属製品",
    "Trucking": "19 陸運業",
    "Waste Management": "28 サービス業",
    "Marine Shipping": "20 海運業",
    "Integrated Freight & Logistics": "22 倉庫・運輸関連業",
    # Basic Materials
    "Basic Materials": "7 化学",
    "Aluminum": "13 非鉄金属",
    "Building Materials": "11 ガラス・土石製品",
    "Chemicals": "7 化学",
    "Specialty Chemicals": "7 化学",
    "Coking Coal": "2 鉱業",
    "Copper": "13 非鉄金属",
    "Gold": "2 鉱業",
    "Lumber & Wood Production": "6 パルプ・紙",
    "Paper & Paper Products": "6 パルプ・紙",
    "Silver": "2 鉱業",
    "Steel": "12 鉄鋼",
    "Other Industrial Metals & Mining": "13 非鉄金属",
    "Other Precious Metals & Mining": "2 鉱業",
    # Real Estate
    "Real Estate": "29 不動産業",
    "REIT—Diversified": "29 不動産業",
    "REIT—Healthcare Facilities": "29 不動産業",
    "REIT—Hotel & Motel": "29 不動産業",
    "REIT—Industrial": "29 不動産業",
    "REIT—Office": "29 不動産業",
    "REIT—Residential": "29 不動産業",
    "REIT—Retail": "29 不動産業",
    "REIT—Specialty": "29 不動産業",
    "Real Estate—Development": "29 不動産業",
    "Real Estate—Diversified": "29 不動産業",
    "Real Estate Services": "29 不動産業",
    # Consumer Defensive
    "Consumer Defensive": "4 食料品",
    "Beverages—Brewers": "4 食料品",
    "Beverages—Non-Alcoholic": "4 食料品",
    "Beverages—Wineries & Distilleries": "4 食料品",
    "Confectioners": "4 食料品",
    "Discount Stores": "27 小売業",
    "Education & Training Services": "28 サービス業",
    "Farm Products": "1 水産・農林業",
    "Food Distribution": "27 小売業",
    "Grocery Stores": "27 小売業",
    "Household & Personal Products": "7 化学",
    "Packaged Foods": "4 食料品",
    "Tobacco": "4 食料品",
    # Utilities
    "Utilities": "18 電気・ガス業",
    "Utilities—Diversified": "18 電気・ガス業",
    "Utilities—Independent Power Producers": "18 電気・ガス業",
    "Utilities—Regulated Electric": "18 電気・ガス業",
    "Utilities—Regulated Gas": "18 電気・ガス業",
    "Utilities—Regulated Water": "18 電気・ガス業",
    "Utilities—Renewable": "18 電気・ガス業",
}


def get_industry_data(sector, industry):
    """企業のセクター・業種から日本の業界平均データを取得"""
    industry_averages = load_industry_averages()
    if not industry_averages:
        return None

    mapped_industry_key = None

    # まず詳細な業種でマッピング
    if industry and industry in SECTOR_TO_INDUSTRY_MAP:
        mapped_industry_key = SECTOR_TO_INDUSTRY_MAP[industry]
        if mapped_industry_key in industry_averages:
            result = industry_averages[mapped_industry_key].copy()
            result["industry_name"] = mapped_industry_key
            return result

    # 次にセクターでマッピング
    if sector and sector in SECTOR_TO_INDUSTRY_MAP:
        mapped_industry_key = SECTOR_TO_INDUSTRY_MAP[sector]
        if mapped_industry_key in industry_averages:
            result = industry_averages[mapped_industry_key].copy()
            result["industry_name"] = mapped_industry_key
            return result

    return None


def get_sector_market_cap(industry_name):
    """業種名から時価総額データを取得"""
    market_cap_data = load_market_cap_by_sector()
    if not market_cap_data:
        return None

    # 業種名から日本語部分を抽出（"17 輸送用機器" -> "輸送用機器"）
    if industry_name:
        # 数字とスペースを除去
        sector_name = industry_name.split()[-1] if " " in industry_name else industry_name
        return market_cap_data.get(sector_name, None)

    return None


def get_company_rank(product_code):
    """企業コードから時価総額ランキングを取得"""
    ranking_data = load_top_companies_by_market_cap()
    if not ranking_data:
        return None

    # コードでマッチング
    for company in ranking_data:
        if company["code"] == str(product_code):
            return company

    return None


def get_financial_cache_filename(product_code):
    """財務情報キャッシュのファイル名を生成"""
    return os.path.join(CACHE_DIR, f"{product_code}_financial.json")


def is_cache_valid(cache_file, max_age_hours=24):
    """キャッシュが有効かチェック（24時間以内）"""
    if not os.path.exists(cache_file):
        return False

    file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
    age = datetime.now() - file_time
    return age.total_seconds() / 3600 < max_age_hours


def load_financial_from_cache(cache_file):
    """JSONキャッシュから財務情報を読み込み"""
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # DataFrameに変換
        result = {
            "info": data.get("info", {}),
            "financials": pd.DataFrame(data.get("financials", {})),
            "balance_sheet": pd.DataFrame(data.get("balance_sheet", {})),
            "cashflow": pd.DataFrame(data.get("cashflow", {})),
        }
        # インデックスを日付型に変換
        for key in ["financials", "balance_sheet", "cashflow"]:
            if not result[key].empty and "index" in data.get(key, {}):
                result[key].columns = pd.to_datetime(data[key]["columns"])
        return result
    except Exception as e:
        st.warning(f"財務キャッシュ読み込みエラー: {e!s}")
        return None


def save_financial_to_cache(ticker, cache_file):
    """財務情報をJSONキャッシュに保存"""
    try:
        data = {
            "info": ticker.info,
            "financials": {
                "columns": [str(col) for col in ticker.financials.columns],
                "data": ticker.financials.to_dict(),
            }
            if not ticker.financials.empty
            else {},
            "balance_sheet": {
                "columns": [str(col) for col in ticker.balance_sheet.columns],
                "data": ticker.balance_sheet.to_dict(),
            }
            if not ticker.balance_sheet.empty
            else {},
            "cashflow": {"columns": [str(col) for col in ticker.cashflow.columns], "data": ticker.cashflow.to_dict()}
            if not ticker.cashflow.empty
            else {},
        }

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return True
    except Exception as e:
        st.warning(f"財務キャッシュ保存エラー: {e!s}")
        return False


def load_financial_data(product_code, force_refresh=False):
    """財務情報を取得（キャッシュ対応）"""
    import yfinance as yf

    cache_file = get_financial_cache_filename(product_code)

    # キャッシュが有効で強制更新でない場合はキャッシュから読み込み
    if not force_refresh and is_cache_valid(cache_file):
        cached_data = load_financial_from_cache(cache_file)
        if cached_data is not None:
            file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            st.info(f"📂 財務情報をキャッシュから読み込み（取得日時: {file_time.strftime('%Y-%m-%d %H:%M:%S')}）")
            return cached_data

    # APIから取得
    try:
        ticker = yf.Ticker(f"{product_code}.T")

        # データが取得できたか確認
        if ticker.info and len(ticker.info) > 1:
            # キャッシュに保存
            if save_financial_to_cache(ticker, cache_file):
                st.success(f"💾 財務情報をキャッシュに保存しました")

            return {
                "info": ticker.info,
                "financials": ticker.financials,
                "balance_sheet": ticker.balance_sheet,
                "cashflow": ticker.cashflow,
            }
        else:
            # APIが失敗した場合、古いキャッシュでも使用
            if os.path.exists(cache_file):
                cached_data = load_financial_from_cache(cache_file)
                if cached_data is not None:
                    st.warning("⚠️ API取得失敗。古いキャッシュを使用します")
                    return cached_data
            return None

    except Exception as e:
        # エラー時も古いキャッシュを試す
        if os.path.exists(cache_file):
            cached_data = load_financial_from_cache(cache_file)
            if cached_data is not None:
                st.warning(f"⚠️ API取得エラー。古いキャッシュを使用します: {e!s}")
                return cached_data
        raise e


def load_from_cache(cache_file):
    """CSVキャッシュからデータを読み込み"""
    try:
        df = pd.read_csv(cache_file)
        df["time"] = pd.to_datetime(df["time"])
        return df
    except Exception as e:
        st.warning(f"キャッシュ読み込みエラー: {e!s}")
        return None


def save_to_cache(df, cache_file):
    """データをCSVキャッシュに保存"""
    try:
        df.to_csv(cache_file, index=False)
        return True
    except Exception as e:
        st.warning(f"キャッシュ保存エラー: {e!s}")
        return False


# データ取得関数（キャッシュ対応）
def load_chart_data(product_code, period_days, duration, force_refresh=False):
    """Yahoo Financeからデータを取得（CSVキャッシュ付き）"""
    cache_file = get_cache_filename(product_code, period_days, duration)

    # キャッシュが有効で強制更新でない場合はキャッシュから読み込み
    if not force_refresh and is_cache_valid(cache_file):
        df = load_from_cache(cache_file)
        if df is not None:
            file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            st.info(f"📂 キャッシュからデータを読み込み（取得日時: {file_time.strftime('%Y-%m-%d %H:%M:%S')}）")
            return df

    # APIからデータ取得
    duration_time = constants.TRADE_MAP.get(duration, {}).get("duration", constants.DURATION_1M)

    yahoo_candles = fetch_yahoo_data(
        product_code=product_code, period_days=period_days, duration=duration_time, market="T"
    )

    if not yahoo_candles:
        # APIが失敗した場合、古いキャッシュでも使用
        if os.path.exists(cache_file):
            df = load_from_cache(cache_file)
            if df is not None:
                st.warning("⚠️ API取得失敗。古いキャッシュを使用します")
                return df
        return None

    # DataFrameに変換
    data = []
    for candle in yahoo_candles:
        data.append(
            {
                "time": candle.time,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            }
        )

    df = pd.DataFrame(data)
    df["time"] = pd.to_datetime(df["time"])

    # CSVに保存
    if save_to_cache(df, cache_file):
        st.success(f"💾 データをキャッシュに保存しました")

    return df


# テクニカル指標計算
def calculate_sma(df, periods):
    """SMAを計算"""
    result = {}
    for period in periods:
        result[f"SMA{period}"] = df["close"].rolling(window=period).mean()
    return result


def calculate_ema(df, periods):
    """EMAを計算"""
    result = {}
    for period in periods:
        result[f"EMA{period}"] = df["close"].ewm(span=period, adjust=False).mean()
    return result


def calculate_bollinger_bands(df, period=20, std=2):
    """Bollinger Bandsを計算"""
    sma = df["close"].rolling(window=period).mean()
    rolling_std = df["close"].rolling(window=period).std()

    upper = sma + (rolling_std * std)
    lower = sma - (rolling_std * std)

    return sma, upper, lower


# バックテスト実行関数
def run_backtest_analysis(product_code, period_days, duration, indicators, detailed=False):
    """バックテストを実行して結果を保存"""
    from itertools import product

    from app.strategy.engine import StrategyEngine, compile_strategy
    from enhanced_backtest import RiskManagement

    timestamp = datetime.now()
    timestamp_iso = timestamp.isoformat()
    timestamp_label = timestamp.strftime("%Y%m%d_%H%M%S")

    risk = RiskManagement(
        initial_capital=1_000_000,
        transaction_cost_percent=0.1,
        slippage_percent=0.02,
    )

    engine = StrategyEngine.from_yahoo(
        product_code=product_code,
        period_days=period_days,
        duration=duration,
        market="T",
        risk_management=risk,
    )

    strategy_specs = {
        "ema": {
            "code": """
def strategy(ctx, params):
    ta = ctx.ta
    fast_n = int(params.get('period1', 12))
    slow_n = int(params.get('period2', 26))
    fast = ta.ema(ctx.close, fast_n)
    slow = ta.ema(ctx.close, slow_n)
    if ta.crossover(fast, slow) and ctx.position == 0:
        ctx.strategy.entry('long', ctx.strategy.long)
    elif ta.crossunder(fast, slow) and ctx.position == 1:
        ctx.strategy.close('long')
""",
            "params": [
                {"period1": p1, "period2": p2}
                for p1, p2 in product([5, 7, 10, 12, 14, 20], [20, 26, 30, 50, 75])
                if p1 < p2
            ],
        },
        "bollinger_bands": {
            "code": """
def strategy(ctx, params):
    ta = ctx.ta
    n = int(params.get('n', 20))
    k = float(params.get('k', 2.0))
    upper, middle, lower = ta.bbands(ctx.close, n, k)
    price = ctx.close[ctx.index]
    if price != price:
        return
    if price < lower[ctx.index] and ctx.position == 0:
        ctx.strategy.entry('long', ctx.strategy.long)
    elif price > upper[ctx.index] and ctx.position == 1:
        ctx.strategy.close('long')
""",
            "params": [{"n": n, "k": k} for n, k in product([10, 20, 30], [1.5, 2.0, 2.5])],
        },
        "ichimoku": {
            "code": """
def strategy(ctx, params):
    ta = ctx.ta
    conv = ta.sma((ctx.high + ctx.low) / 2.0, 9)
    base = ta.sma((ctx.high + ctx.low) / 2.0, 26)
    if ta.crossover(conv, base) and ctx.position == 0:
        ctx.strategy.entry('long', ctx.strategy.long)
    elif ta.crossunder(conv, base) and ctx.position == 1:
        ctx.strategy.close('long')
""",
            "params": [{}],
        },
        "rsi": {
            "code": """
def strategy(ctx, params):
    ta = ctx.ta
    period = int(params.get('period', 14))
    buy_thr = float(params.get('buy_threshold', 30))
    sell_thr = float(params.get('sell_threshold', 70))
    rsi = ta.rsi(ctx.close, period)
    value = rsi[ctx.index]
    if value != value:
        return
    if value < buy_thr and ctx.position == 0:
        ctx.strategy.entry('long', ctx.strategy.long)
    elif value > sell_thr and ctx.position == 1:
        ctx.strategy.close('long')
""",
            "params": [
                {"period": period, "buy_threshold": buy_thr, "sell_threshold": sell_thr}
                for period, buy_thr, sell_thr in product([8, 14, 21], [20, 25, 30], [65, 70, 75])
                if buy_thr < sell_thr
            ],
        },
        "macd": {
            "code": """
def strategy(ctx, params):
    ta = ctx.ta
    fast = int(params.get('fast_period', 12))
    slow = int(params.get('slow_period', 26))
    signal = int(params.get('signal_period', 9))
    macd_line, signal_line, _ = ta.macd(ctx.close, fast, slow, signal)
    if ta.crossover(macd_line, signal_line) and ctx.position == 0:
        ctx.strategy.entry('long', ctx.strategy.long)
    elif ta.crossunder(macd_line, signal_line) and ctx.position == 1:
        ctx.strategy.close('long')
""",
            "params": [
                {"fast_period": fast, "slow_period": slow, "signal_period": signal}
                for fast, slow, signal in product([8, 12], [17, 26], [5, 9])
                if fast < slow
            ],
        },
    }

    enabled = {
        "ema": bool(indicators.get("ema", False)),
        "bollinger_bands": bool(indicators.get("bb", False)),
        "ichimoku": bool(indicators.get("ichimoku", False)),
        "rsi": bool(indicators.get("rsi", False)),
        "macd": bool(indicators.get("macd", False)),
    }

    summary_results = {}
    detailed_results = {}

    for strategy_name, spec in strategy_specs.items():
        if not enabled.get(strategy_name):
            continue

        strategy_fn = compile_strategy(spec["code"])
        all_rows = []

        for params in spec["params"]:
            result = engine.run(strategy_fn, params)
            perf = float(result.get("risk_management_stats", {}).get("return_percent", 0.0))

            row = {**params}
            row["performance"] = perf
            row["total_trades"] = int(result.get("total_trades", 0))
            row["win_rate"] = float(result.get("metrics", {}).get("win_rate", 0.0))
            row["max_drawdown"] = float(result.get("metrics", {}).get("max_drawdown", 0.0))
            row["sharpe_ratio"] = float(result.get("metrics", {}).get("sharpe_ratio", 0.0))
            all_rows.append(row)

        if not all_rows:
            continue

        best = max(all_rows, key=lambda x: x["performance"])

        summary_entry = {k: v for k, v in best.items() if k not in ["total_trades", "win_rate", "max_drawdown", "sharpe_ratio"]}
        summary_results[strategy_name] = summary_entry

        if detailed:
            best_params = {k: v for k, v in best.items() if k not in ["performance", "total_trades", "win_rate", "max_drawdown", "sharpe_ratio"]}
            detailed_results[strategy_name] = {
                "best_performance": float(best["performance"]),
                "best_params": best_params,
                "all_results": all_rows,
            }

            detail_df = pd.DataFrame(all_rows).sort_values("performance", ascending=False)
            detail_path = os.path.join(BACKTEST_DETAILS_DIR, f"{product_code}_{strategy_name}_{timestamp_label}.csv")
            detail_df.to_csv(detail_path, index=False, encoding="utf-8-sig")

    output = {
        "product_code": product_code,
        "period_days": period_days,
        "duration": duration,
        "timestamp": timestamp_iso,
        "results": summary_results,
    }

    if detailed:
        output["detailed_results"] = detailed_results

    result_dir = os.path.dirname(BACKTEST_RESULTS_FILE)
    if result_dir:
        os.makedirs(result_dir, exist_ok=True)

    with open(BACKTEST_RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    return summary_results, detailed_results if detailed else None


# バックテスト結果読み込み
def load_backtest_results():
    """backtest_results.jsonを読み込み"""
    results_file = BACKTEST_RESULTS_FILE

    if not os.path.exists(results_file) and os.path.exists("backtest_results.json"):
        results_file = "backtest_results.json"

    if not os.path.exists(results_file):
        return None

    try:
        with open(results_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"エラー: {e}")
        return None


# トレードシグナル生成（簡易版）
def generate_signals(df, sma_short=7, sma_long=14):
    """SMAクロスオーバーでシグナルを生成"""
    df["SMA_short"] = df["close"].rolling(window=sma_short).mean()
    df["SMA_long"] = df["close"].rolling(window=sma_long).mean()

    signals = []
    for i in range(1, len(df)):
        if pd.notna(df["SMA_short"].iloc[i]) and pd.notna(df["SMA_long"].iloc[i]):
            # ゴールデンクロス（買いシグナル）
            if (
                df["SMA_short"].iloc[i - 1] <= df["SMA_long"].iloc[i - 1]
                and df["SMA_short"].iloc[i] > df["SMA_long"].iloc[i]
            ):
                signals.append({"time": df["time"].iloc[i], "price": df["close"].iloc[i], "type": "buy"})
            # デッドクロス（売りシグナル）
            elif (
                df["SMA_short"].iloc[i - 1] >= df["SMA_long"].iloc[i - 1]
                and df["SMA_short"].iloc[i] < df["SMA_long"].iloc[i]
            ):
                signals.append({"time": df["time"].iloc[i], "price": df["close"].iloc[i], "type": "sell"})

    return pd.DataFrame(signals) if signals else pd.DataFrame()


# メインエリア
if data_source == "Yahoo Finance":
    # データ取得
    if st.session_state.reload_data:
        force_refresh_flag = st.session_state.get("force_refresh", False)
        with st.spinner("データ取得中..."):
            df = load_chart_data(product_code, period_days, duration, force_refresh=force_refresh_flag)
            st.session_state.reload_data = False

            if df is not None:
                st.session_state.chart_data = df
                st.success(f"✅ データ取得成功: {len(df)}件のローソク足データ")
            else:
                st.error("❌ データ取得に失敗しました")

    # チャート表示
    if "chart_data" in st.session_state:
        df = st.session_state.chart_data.copy()

        # 統計情報表示
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("データ数", f"{len(df)}本")
        with col2:
            st.metric("最新価格", f"{df['close'].iloc[-1]:.2f}")
        with col3:
            change = df["close"].iloc[-1] - df["close"].iloc[0]
            change_pct = (change / df["close"].iloc[0]) * 100
            st.metric("変化", f"{change:.2f}", f"{change_pct:+.2f}%")
        with col4:
            st.metric("最高値", f"{df['high'].max():.2f}")

        # テクニカル指標を計算
        indicators = {}
        if show_sma and sma_periods:
            indicators["sma"] = calculate_sma(df, sma_periods)
        if show_ema and ema_periods:
            indicators["ema"] = calculate_ema(df, ema_periods)
        if show_bbands:
            bb_sma, bb_upper, bb_lower = calculate_bollinger_bands(df, bb_period, bb_std)
            indicators["bb"] = {"sma": bb_sma, "upper": bb_upper, "lower": bb_lower}

        # トレードシグナルを生成
        signals = pd.DataFrame()
        if show_sma and len(sma_periods) >= 2:
            signals = generate_signals(df, min(sma_periods), max(sma_periods))

        # サブプロット作成（チャート + 出来高）
        if show_volume:
            fig = make_subplots(
                rows=2,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.7, 0.3],
                subplot_titles=(f"{product_code} - {duration}足", "出来高"),
            )
            volume_row = 2
        else:
            fig = go.Figure()
            volume_row = None

        # ローソク足チャート
        candlestick = go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
            name="OHLC",
        )

        if show_volume:
            fig.add_trace(candlestick, row=1, col=1)
        else:
            fig.add_trace(candlestick)

        # SMAを追加
        if "sma" in indicators:
            colors = ["#2962ff", "#ff6d00", "#00e676", "#aa00ff", "#ffd600"]
            for idx, (name, values) in enumerate(indicators["sma"].items()):
                trace = go.Scatter(
                    x=df["time"], y=values, name=name, line=dict(color=colors[idx % len(colors)], width=2), mode="lines"
                )
                if show_volume:
                    fig.add_trace(trace, row=1, col=1)
                else:
                    fig.add_trace(trace)

        # EMAを追加
        if "ema" in indicators:
            colors = ["#00bcd4", "#e91e63", "#4caf50", "#ff5722"]
            for idx, (name, values) in enumerate(indicators["ema"].items()):
                trace = go.Scatter(
                    x=df["time"],
                    y=values,
                    name=name,
                    line=dict(color=colors[idx % len(colors)], width=2, dash="dash"),
                    mode="lines",
                )
                if show_volume:
                    fig.add_trace(trace, row=1, col=1)
                else:
                    fig.add_trace(trace)

        # Bollinger Bandsを追加
        if "bb" in indicators:
            bb = indicators["bb"]
            # 上限バンド
            trace_upper = go.Scatter(
                x=df["time"],
                y=bb["upper"],
                name="BB Upper",
                line=dict(color="rgba(250, 128, 114, 0.5)", width=1),
                mode="lines",
            )
            # 下限バンド
            trace_lower = go.Scatter(
                x=df["time"],
                y=bb["lower"],
                name="BB Lower",
                line=dict(color="rgba(250, 128, 114, 0.5)", width=1),
                fill="tonexty",
                fillcolor="rgba(250, 128, 114, 0.1)",
                mode="lines",
            )
            # 中央線
            trace_sma = go.Scatter(
                x=df["time"],
                y=bb["sma"],
                name="BB SMA",
                line=dict(color="rgba(250, 128, 114, 0.8)", width=1),
                mode="lines",
            )

            if show_volume:
                fig.add_trace(trace_upper, row=1, col=1)
                fig.add_trace(trace_sma, row=1, col=1)
                fig.add_trace(trace_lower, row=1, col=1)
            else:
                fig.add_trace(trace_upper)
                fig.add_trace(trace_sma)
                fig.add_trace(trace_lower)

        # トレードシグナルを追加
        if not signals.empty:
            buy_signals = signals[signals["type"] == "buy"]
            sell_signals = signals[signals["type"] == "sell"]

            if not buy_signals.empty:
                trace_buy = go.Scatter(
                    x=buy_signals["time"],
                    y=buy_signals["price"],
                    mode="markers",
                    name="買いシグナル",
                    marker=dict(symbol="triangle-up", size=15, color="#26a69a", line=dict(color="white", width=2)),
                )
                if show_volume:
                    fig.add_trace(trace_buy, row=1, col=1)
                else:
                    fig.add_trace(trace_buy)

            if not sell_signals.empty:
                trace_sell = go.Scatter(
                    x=sell_signals["time"],
                    y=sell_signals["price"],
                    mode="markers",
                    name="売りシグナル",
                    marker=dict(symbol="triangle-down", size=15, color="#ef5350", line=dict(color="white", width=2)),
                )
                if show_volume:
                    fig.add_trace(trace_sell, row=1, col=1)
                else:
                    fig.add_trace(trace_sell)

        # 出来高チャート
        if show_volume:
            colors = [
                "#ef5350" if close < open else "#26a69a" for close, open in zip(df["close"], df["open"], strict=False)
            ]

            fig.add_trace(
                go.Bar(x=df["time"], y=df["volume"], name="出来高", marker_color=colors, showlegend=False), row=2, col=1
            )

        # レイアウト設定
        layout_args = dict(
            height=chart_height,
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            # X軸の範囲を自動調整（全データを表示）
            xaxis=dict(range=[df["time"].min(), df["time"].max()], type="date"),
        )

        if show_volume:
            fig.update_xaxes(title_text="時刻", row=2, col=1, range=[df["time"].min(), df["time"].max()])
            fig.update_xaxes(title_text="", row=1, col=1, range=[df["time"].min(), df["time"].max()])
            fig.update_yaxes(title_text="価格", row=1, col=1)
            fig.update_yaxes(title_text="出来高", row=2, col=1)
        else:
            layout_args["xaxis_title"] = "時刻"
            layout_args["yaxis_title"] = "価格"

        fig.update_layout(**layout_args)

        st.plotly_chart(fig, width="stretch")

        # シグナル統計
        if not signals.empty:
            st.divider()
            st.subheader("🎯 トレードシグナル統計")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("総シグナル数", len(signals))
            with col2:
                st.metric("買いシグナル", len(signals[signals["type"] == "buy"]))
            with col3:
                st.metric("売りシグナル", len(signals[signals["type"] == "sell"]))

            # 最新シグナル表示
            st.write("**最新のシグナル（最大10件）:**")
            st.dataframe(signals.tail(10).sort_values("time", ascending=False), width="stretch", hide_index=True)

        # 財務情報セクション（シグナルブロックの外）
        st.divider()
        st.header("💼 財務情報・企業分析")

        try:
            # 強制更新フラグを取得
            force_refresh = st.session_state.get("force_refresh", False)

            # キャッシュ対応の財務情報取得
            financial_data = load_financial_data(product_code, force_refresh)

            if financial_data is None:
                st.warning("財務情報を取得できませんでした")
            else:
                info = financial_data["info"]
                income_stmt = financial_data["financials"]
                balance_sheet = financial_data["balance_sheet"]
                cashflow_stmt = financial_data["cashflow"]

                # 企業基本情報
                st.subheader("🏢 企業概要")
                info_col1, info_col2, info_col3 = st.columns(3)

            with info_col1:
                st.write("**企業名**")
                st.write(info.get("longName", "N/A"))
                st.write("**セクター**")
                st.write(info.get("sector", "N/A"))
                st.write("**業種**")
                st.write(info.get("industry", "N/A"))

            with info_col2:
                st.write("**従業員数**")
                employees = info.get("fullTimeEmployees", 0)
                if employees:
                    st.write(f"{employees:,}人")
                else:
                    st.write("N/A")
                st.write("**本社所在地**")
                st.write(info.get("country", "N/A"))
                st.write("**ウェブサイト**")
                website = info.get("website", "")
                if website:
                    st.markdown(f"[{website}]({website})")
                else:
                    st.write("N/A")

            with info_col3:
                st.write("**上場市場**")
                st.write(info.get("exchange", "N/A"))
                st.write("**通貨**")
                st.write(info.get("currency", "JPY"))
                st.write("**52週高値/安値**")
                high_52 = info.get("fiftyTwoWeekHigh", 0)
                low_52 = info.get("fiftyTwoWeekLow", 0)
                if high_52 and low_52:
                    st.write(f"¥{high_52:.2f} / ¥{low_52:.2f}")
                else:
                    st.write("N/A")

            st.divider()

            # 主要財務指標（拡張版）
            st.subheader("📊 主要財務指標")

            # 1行目: バリュエーション指標
            st.write("**🏷️ バリュエーション指標**")
            val_col1, val_col2, val_col3, val_col4, val_col5 = st.columns(5)

            with val_col1:
                market_cap = info.get("marketCap", 0)
                if market_cap:
                    st.metric(
                        "時価総額", f"¥{market_cap/1e12:.2f}兆" if market_cap > 1e12 else f"¥{market_cap/1e8:.1f}億"
                    )
                else:
                    st.metric("時価総額", "N/A")

            with val_col2:
                pe_ratio = info.get("trailingPE", None)
                if pe_ratio:
                    st.metric("PER", f"{pe_ratio:.2f}x")
                else:
                    st.metric("PER", "N/A")

            with val_col3:
                pb_ratio = info.get("priceToBook", None)
                if pb_ratio:
                    st.metric("PBR", f"{pb_ratio:.2f}x")
                else:
                    st.metric("PBR", "N/A")

            with val_col4:
                ps_ratio = info.get("priceToSalesTrailing12Months", None)
                if ps_ratio:
                    st.metric("PSR", f"{ps_ratio:.2f}x")
                else:
                    st.metric("PSR", "N/A")

            with val_col5:
                ev_ebitda = info.get("enterpriseToEbitda", None)
                if ev_ebitda:
                    st.metric("EV/EBITDA", f"{ev_ebitda:.2f}x")
                else:
                    st.metric("EV/EBITDA", "N/A")

            # 2行目: 収益性指標
            st.write("**💰 収益性指標**")
            prof_col1, prof_col2, prof_col3, prof_col4, prof_col5 = st.columns(5)

            with prof_col1:
                roe = info.get("returnOnEquity", None)
                if roe:
                    st.metric("ROE", f"{roe*100:.2f}%")
                else:
                    st.metric("ROE", "N/A")

            with prof_col2:
                roa = info.get("returnOnAssets", None)
                if roa:
                    st.metric("ROA", f"{roa*100:.2f}%")
                else:
                    st.metric("ROA", "N/A")

            with prof_col3:
                profit_margin = info.get("profitMargins", None)
                if profit_margin:
                    st.metric("純利益率", f"{profit_margin*100:.2f}%")
                else:
                    st.metric("純利益率", "N/A")

            with prof_col4:
                operating_margin = info.get("operatingMargins", None)
                if operating_margin:
                    st.metric("営業利益率", f"{operating_margin*100:.2f}%")
                else:
                    st.metric("営業利益率", "N/A")

            with prof_col5:
                gross_margin = info.get("grossMargins", None)
                if gross_margin:
                    st.metric("粗利益率", f"{gross_margin*100:.2f}%")
                else:
                    st.metric("粗利益率", "N/A")

            # 3行目: 成長性指標
            st.write("**📈 成長性指標**")
            growth_col1, growth_col2, growth_col3, growth_col4, growth_col5 = st.columns(5)

            with growth_col1:
                revenue_growth = info.get("revenueGrowth", None)
                if revenue_growth:
                    st.metric("売上成長率", f"{revenue_growth*100:.2f}%")
                else:
                    st.metric("売上成長率", "N/A")

            with growth_col2:
                earnings_growth = info.get("earningsGrowth", None)
                if earnings_growth:
                    st.metric("利益成長率", f"{earnings_growth*100:.2f}%")
                else:
                    st.metric("利益成長率", "N/A")

            with growth_col3:
                earnings_quarterly = info.get("earningsQuarterlyGrowth", None)
                if earnings_quarterly:
                    st.metric("四半期利益成長率", f"{earnings_quarterly*100:.2f}%")
                else:
                    st.metric("四半期利益成長率", "N/A")

            with growth_col4:
                revenue_per_share = info.get("revenuePerShare", None)
                if revenue_per_share:
                    st.metric("1株売上", f"¥{revenue_per_share:.2f}")
                else:
                    st.metric("1株売上", "N/A")

            with growth_col5:
                book_value = info.get("bookValue", None)
                if book_value:
                    st.metric("1株純資産", f"¥{book_value:.2f}")
                else:
                    st.metric("1株純資産", "N/A")

            # 4行目: 配当・株主還元
            st.write("**💵 配当・株主還元**")
            div_col1, div_col2, div_col3, div_col4, div_col5 = st.columns(5)

            with div_col1:
                div_yield = info.get("dividendYield", None)
                if div_yield:
                    st.metric("配当利回り", f"{div_yield*100:.2f}%")
                else:
                    st.metric("配当利回り", "N/A")

            with div_col2:
                div_rate = info.get("dividendRate", None)
                if div_rate:
                    st.metric("年間配当", f"¥{div_rate:.2f}")
                else:
                    st.metric("年間配当", "N/A")

            with div_col3:
                payout_ratio = info.get("payoutRatio", None)
                if payout_ratio:
                    st.metric("配当性向", f"{payout_ratio*100:.2f}%")
                else:
                    st.metric("配当性向", "N/A")

            with div_col4:
                ex_dividend_date = info.get("exDividendDate", None)
                if ex_dividend_date:
                    from datetime import datetime

                    date_str = datetime.fromtimestamp(ex_dividend_date).strftime("%Y-%m-%d")
                    st.metric("権利落ち日", date_str)
                else:
                    st.metric("権利落ち日", "N/A")

            with div_col5:
                trailing_eps = info.get("trailingEps", None)
                if trailing_eps:
                    st.metric("EPS (実績)", f"¥{trailing_eps:.2f}")
                else:
                    st.metric("EPS (実績)", "N/A")

            # 5行目: 財務健全性
            st.write("**🏦 財務健全性**")
            health_col1, health_col2, health_col3, health_col4, health_col5, health_col6 = st.columns(6)

            with health_col1:
                # 自己資本比率を計算
                total_stockholder_equity = info.get("totalStockholderEquity", None)
                total_assets = info.get("totalAssets", None)
                if total_stockholder_equity and total_assets and total_assets > 0:
                    equity_ratio = (total_stockholder_equity / total_assets) * 100
                    st.metric(
                        "自己資本比率", f"{equity_ratio:.2f}%", help="総資産に占める自己資本の割合。高いほど財務が安定"
                    )
                else:
                    st.metric("自己資本比率", "N/A")

            with health_col2:
                debt_to_equity = info.get("debtToEquity", None)
                if debt_to_equity:
                    st.metric("負債資本倍率", f"{debt_to_equity:.2f}")
                else:
                    st.metric("負債資本倍率", "N/A")

            with health_col3:
                current_ratio = info.get("currentRatio", None)
                if current_ratio:
                    st.metric("流動比率", f"{current_ratio:.2f}")
                else:
                    st.metric("流動比率", "N/A")

            with health_col4:
                quick_ratio = info.get("quickRatio", None)
                if quick_ratio:
                    st.metric("当座比率", f"{quick_ratio:.2f}")
                else:
                    st.metric("当座比率", "N/A")

            with health_col5:
                total_cash = info.get("totalCash", None)
                if total_cash:
                    st.metric("現金等価物", f"¥{total_cash/1e8:.1f}億")
                else:
                    st.metric("現金等価物", "N/A")

            with health_col6:
                total_debt = info.get("totalDebt", None)
                if total_debt:
                    st.metric("総負債", f"¥{total_debt/1e8:.1f}億")
                else:
                    st.metric("総負債", "N/A")

            st.divider()

            # 業界平均・市場比較セクション
            st.subheader("📊 業界平均・市場比較")

            # セクター情報を取得
            sector = info.get("sector", None)
            industry = info.get("industry", None)

            # 業界平均データを取得
            industry_data = get_industry_data(sector, industry)

            # 追加データを取得
            sector_market_cap = None
            company_rank = None

            if industry_data and "industry_name" in industry_data:
                sector_market_cap = get_sector_market_cap(industry_data["industry_name"])

            company_rank = get_company_rank(product_code)

            if sector or industry:
                # 業界情報の表示
                info_parts = [f"**セクター:** {sector or 'N/A'}", f"**業種:** {industry or 'N/A'}"]

                if industry_data:
                    info_parts.append(
                        f"**業界:** {industry_data.get('industry_name', 'N/A')} "
                        f"({industry_data.get('companies', 0)}社)"
                    )

                if sector_market_cap:
                    market_cap_trillion = sector_market_cap.get("market_cap_trillion", 0)
                    info_parts.append(f"**業界時価総額:** {market_cap_trillion:.2f}兆円")

                if company_rank:
                    info_parts.append(
                        f"**市場ランキング:** 第{company_rank['rank']}位 "
                        f"(時価総額: {company_rank['market_cap_trillion']:.2f}兆円)"
                    )

                st.write(" | ".join(info_parts))

                if not industry_data:
                    st.info("💡 業界平均データが見つかりません。参考値を表示します。")

                # 比較指標の表示
                comp_tab1, comp_tab2, comp_tab3 = st.tabs(["📈 主要指標比較", "🏆 業界内ランキング", "📊 業界詳細"])

                with comp_tab1:
                    st.write("#### 主要財務指標の比較")

                    # 比較データを準備
                    comparison_data = []

                    # PER比較
                    company_pe = info.get("trailingPE", None)
                    industry_pe_jp = industry_data.get("per") if industry_data else None

                    if company_pe:
                        comparison_data.append(
                            {
                                "指標": "PER",
                                "当社": f"{company_pe:.2f}x",
                                "業界平均": f"{industry_pe_jp:.2f}x" if industry_pe_jp else "N/A",
                                "日経平均": "18.6x (プライム総合)",
                                "判定": "割安"
                                if industry_pe_jp and company_pe < industry_pe_jp
                                else "割高"
                                if industry_pe_jp and company_pe > industry_pe_jp
                                else "-",
                            }
                        )

                    # PBR比較
                    company_pb = info.get("priceToBook", None)
                    industry_pb_jp = industry_data.get("pbr") if industry_data else None

                    if company_pb:
                        comparison_data.append(
                            {
                                "指標": "PBR",
                                "当社": f"{company_pb:.2f}x",
                                "業界平均": f"{industry_pb_jp:.2f}x" if industry_pb_jp else "N/A",
                                "日経平均": "1.6x (プライム総合)",
                                "判定": "割安"
                                if industry_pb_jp and company_pb < industry_pb_jp
                                else "割高"
                                if industry_pb_jp and company_pb > industry_pb_jp
                                else "割安"
                                if company_pb < 1.0
                                else "適正",
                            }
                        )

                    # ROE比較
                    company_roe = info.get("returnOnEquity", None)

                    if company_roe:
                        comparison_data.append(
                            {
                                "指標": "ROE",
                                "当社": f"{company_roe*100:.2f}%",
                                "業界平均": "N/A",
                                "セクター平均": "N/A",
                                "日経平均": "9.5% (参考)",
                                "判定": "優良" if company_roe > 0.10 else "標準" if company_roe > 0.05 else "低い",
                            }
                        )

                    # ROA比較
                    company_roa = info.get("returnOnAssets", None)

                    if company_roa:
                        comparison_data.append(
                            {
                                "指標": "ROA",
                                "当社": f"{company_roa*100:.2f}%",
                                "業界平均": "N/A",
                                "セクター平均": "N/A",
                                "日経平均": "5.0% (参考)",
                                "判定": "優良" if company_roa > 0.05 else "標準" if company_roa > 0.02 else "低い",
                            }
                        )

                    # 自己資本比率比較
                    total_stockholder_equity = info.get("totalStockholderEquity", None)
                    total_assets = info.get("totalAssets", None)

                    if total_stockholder_equity and total_assets and total_assets > 0:
                        company_equity_ratio = (total_stockholder_equity / total_assets) * 100
                        comparison_data.append(
                            {
                                "指標": "自己資本比率",
                                "当社": f"{company_equity_ratio:.2f}%",
                                "業界平均": "N/A",
                                "セクター平均": "N/A",
                                "日経平均": "45% (参考)",
                                "判定": "優良"
                                if company_equity_ratio > 50
                                else "標準"
                                if company_equity_ratio > 30
                                else "要注意",
                            }
                        )

                    # 営業利益率比較
                    operating_margin = info.get("operatingMargins", None)

                    if operating_margin:
                        comparison_data.append(
                            {
                                "指標": "営業利益率",
                                "当社": f"{operating_margin*100:.2f}%",
                                "業界平均": "N/A",
                                "セクター平均": "N/A",
                                "日経平均": "8.0% (参考)",
                                "判定": "優良"
                                if operating_margin > 0.10
                                else "標準"
                                if operating_margin > 0.05
                                else "低い",
                            }
                        )

                    # 配当利回り比較
                    dividend_yield = info.get("dividendYield", None)

                    if dividend_yield:
                        comparison_data.append(
                            {
                                "指標": "配当利回り",
                                "当社": f"{dividend_yield*100:.2f}%",
                                "業界平均": "N/A",
                                "セクター平均": "N/A",
                                "日経平均": "2.5% (参考)",
                                "判定": "高配当"
                                if dividend_yield > 0.04
                                else "標準"
                                if dividend_yield > 0.02
                                else "低配当",
                            }
                        )

                    if comparison_data:
                        df_comparison = pd.DataFrame(comparison_data)

                        # スタイル付きテーブル表示
                        st.dataframe(
                            df_comparison,
                            width="stretch",
                            hide_index=True,
                            column_config={
                                "判定": st.column_config.TextColumn(
                                    "判定", help="業界平均や一般基準との比較", width="small"
                                )
                            },
                        )

                        st.caption(
                            "📌 注: 業界平均データは東京証券取引所プライム市場の業種別データ（2025年10月版）を使用しています。"
                            "日経平均はプライム市場総合の参考値です。"
                        )
                    else:
                        st.info("比較データが十分に取得できませんでした")

                    # レーダーチャートで視覚化
                    if len(comparison_data) >= 4:
                        st.write("#### 財務指標レーダーチャート")

                        # 正規化用の関数
                        def normalize_value(value, indicator):
                            """指標を0-100に正規化"""
                            if indicator == "PER":
                                return max(0, min(100, (30 - value) / 30 * 100)) if value else 50
                            elif indicator == "PBR":
                                return max(0, min(100, (3 - value) / 3 * 100)) if value else 50
                            elif indicator in ["ROE", "ROA", "営業利益率"]:
                                return min(100, value * 500) if value else 0  # 20%で100点
                            elif indicator == "自己資本比率":
                                return min(100, value * 1.5) if value else 0  # 67%で100点
                            elif indicator == "配当利回り":
                                return min(100, value * 2000) if value else 0  # 5%で100点
                            return 50

                        # レーダーチャート用データ準備
                        radar_indicators = []
                        radar_values = []
                        radar_industry_values = []  # 業界平均用

                        for item in comparison_data[:6]:  # 最大6指標
                            indicator = item["指標"]
                            value_str = item["当社"]
                            industry_str = item.get("業界平均", "N/A")

                            # 数値を抽出
                            try:
                                if "x" in value_str:
                                    value = float(value_str.replace("x", ""))
                                elif "%" in value_str:
                                    value = float(value_str.replace("%", ""))
                                else:
                                    continue

                                radar_indicators.append(indicator)
                                radar_values.append(normalize_value(value, indicator))

                                # 業界平均の数値も抽出（可能な場合）
                                if industry_str != "N/A":
                                    if "x" in industry_str:
                                        industry_value = float(industry_str.replace("x", ""))
                                    elif "%" in industry_str:
                                        industry_value = float(industry_str.replace("%", ""))
                                    else:
                                        industry_value = None
                                    
                                    if industry_value is not None:
                                        radar_industry_values.append(normalize_value(industry_value, indicator))
                                    else:
                                        radar_industry_values.append(50)  # デフォルト値
                                else:
                                    radar_industry_values.append(50)  # デフォルト値（日経平均参考値として）
                            except:
                                continue

                        if radar_indicators:
                            fig_radar = go.Figure()

                            # 当社のデータ
                            fig_radar.add_trace(
                                go.Scatterpolar(
                                    r=radar_values + [radar_values[0]],  # 閉じるために最初の値を追加
                                    theta=radar_indicators + [radar_indicators[0]],
                                    fill="toself",
                                    name="当社",
                                    line=dict(color="#2962ff", width=3),
                                    fillcolor="rgba(41, 98, 255, 0.3)",
                                )
                            )

                            # 業界平均のデータ
                            if len(radar_industry_values) == len(radar_indicators):
                                legend_name = "業界平均" if industry_data else "日経平均 (参考)"
                                fig_radar.add_trace(
                                    go.Scatterpolar(
                                        r=radar_industry_values + [radar_industry_values[0]],
                                        theta=radar_indicators + [radar_indicators[0]],
                                        fill="toself",
                                        name=legend_name,
                                        line=dict(color="#ff9800", width=2, dash="dash"),
                                        fillcolor="rgba(255, 152, 0, 0.1)",
                                    )
                                )

                            fig_radar.update_layout(
                                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                                showlegend=True,
                                legend=dict(x=0.7, y=1.1, orientation="h"),
                                height=450,
                                title="財務指標スコア比較 (0-100)",
                            )

                            st.plotly_chart(fig_radar, width="stretch")

                with comp_tab2:
                    st.write("#### 業界内での位置づけ")

                    # 簡易的なランキング表示
                    rank_col1, rank_col2, rank_col3 = st.columns(3)

                    with rank_col1:
                        st.metric(
                            "時価総額",
                            f"¥{info.get('marketCap', 0)/1e12:.2f}兆"
                            if info.get("marketCap", 0) > 1e12
                            else f"¥{info.get('marketCap', 0)/1e8:.1f}億",
                            help="セクター内での規模",
                        )

                    with rank_col2:
                        if company_roe:
                            st.metric("ROE", f"{company_roe*100:.2f}%", delta=f"業界平均比 N/A", help="収益性の指標")

                    with rank_col3:
                        if operating_margin:
                            st.metric(
                                "営業利益率",
                                f"{operating_margin*100:.2f}%",
                                delta=f"業界平均比 N/A",
                                help="収益効率の指標",
                            )

                    st.info("📊 より詳細な業界ランキング情報は、証券会社のレポートや専門サイトをご参照ください。")

                with comp_tab3:
                    st.write("#### 業界詳細情報")

                    if industry_data and sector_market_cap:
                        detail_col1, detail_col2 = st.columns(2)

                        with detail_col1:
                            st.write("##### 📊 業界統計")
                            st.metric(
                                "業界名", industry_data.get("industry_name", "N/A"), help="東京証券取引所の業種区分"
                            )
                            st.metric(
                                "上場企業数",
                                f"{industry_data.get('companies', 0)}社",
                                help="プライム市場の企業数",
                            )
                            st.metric(
                                "業界時価総額",
                                f"{sector_market_cap.get('market_cap_trillion', 0):.2f}兆円",
                                help="業界全体の時価総額",
                            )

                            # 1社あたりの平均時価総額
                            if industry_data.get("companies", 0) > 0:
                                avg_market_cap = sector_market_cap.get("market_cap_billion", 0) / industry_data.get(
                                    "companies", 1
                                )
                                st.metric("1社あたり平均時価総額", f"{avg_market_cap:.1f}億円")

                        with detail_col2:
                            st.write("##### 📈 バリュエーション")
                            st.metric(
                                "業界平均PER",
                                f"{industry_data.get('per', 0):.2f}x" if industry_data.get("per") else "N/A",
                                help="株価収益率の業界平均",
                            )
                            st.metric(
                                "業界平均PBR",
                                f"{industry_data.get('pbr', 0):.2f}x" if industry_data.get("pbr") else "N/A",
                                help="株価純資産倍率の業界平均",
                            )

                            # 当社の業界内シェア
                            company_market_cap = info.get("marketCap", 0)
                            if company_market_cap and sector_market_cap:
                                sector_total = sector_market_cap.get("market_cap_million", 1) * 1000000
                                share = (company_market_cap / sector_total) * 100 if sector_total > 0 else 0
                                st.metric(
                                    "当社の業界シェア", f"{share:.2f}%", help="業界全体の時価総額に占める当社の割合"
                                )

                        # 時価総額ランキング情報
                        if company_rank:
                            st.write("##### 🏆 市場ランキング")
                            rank_info_col1, rank_info_col2, rank_info_col3 = st.columns(3)

                            with rank_info_col1:
                                st.metric("プライム市場順位", f"第{company_rank['rank']}位")

                            with rank_info_col2:
                                st.metric("時価総額", f"{company_rank['market_cap_trillion']:.2f}兆円")

                            with rank_info_col3:
                                # トップ10以内かどうか
                                if company_rank["rank"] <= 10:
                                    st.success("🌟 トップ10企業")
                                elif company_rank["rank"] <= 50:
                                    st.info("⭐ トップ50企業")
                                elif company_rank["rank"] <= 100:
                                    st.info("📊 トップ100企業")

                    elif industry_data:
                        st.write("##### 📊 業界統計")
                        st.write(f"**業界名:** {industry_data.get('industry_name', 'N/A')}")
                        st.write(f"**上場企業数:** {industry_data.get('companies', 0)}社")
                        st.write(f"**業界平均PER:** {industry_data.get('per', 0):.2f}x")
                        st.write(f"**業界平均PBR:** {industry_data.get('pbr', 0):.2f}x")
                    else:
                        st.info("業界詳細データが取得できませんでした")

            else:
                st.info("セクター情報が取得できませんでした")

            st.divider()

            # 財務諸表グラフ（拡張版）
            # すでにload_financial_dataで取得済み

            if not income_stmt.empty or not balance_sheet.empty:
                st.subheader("📊 財務データの推移分析")

                # タブで分類
                fin_tab1, fin_tab2, fin_tab3, fin_tab4 = st.tabs(
                    ["💰 損益計算書", "📊 貸借対照表", "💵 キャッシュフロー", "📈 財務比率"]
                )

                # === 損益計算書タブ ===
                with fin_tab1:
                    if not income_stmt.empty:
                        st.write("#### 売上・利益の推移")

                        # 主要な損益項目
                        pl_col1, pl_col2 = st.columns(2)

                        with pl_col1:
                            # 売上・各種利益の推移
                            pl_items = ["Total Revenue", "Gross Profit", "Operating Income", "Net Income"]
                            available_pl = [item for item in pl_items if item in income_stmt.index]

                            if available_pl:
                                fig_pl = go.Figure()

                                for item in available_pl:
                                    values = income_stmt.loc[item].values / 1e8
                                    dates = [
                                        d.strftime("%Y") if hasattr(d, "strftime") else str(d)
                                        for d in income_stmt.columns
                                    ]

                                    fig_pl.add_trace(
                                        go.Scatter(
                                            x=dates,
                                            y=values,
                                            mode="lines+markers",
                                            name=item.replace("Total Revenue", "売上高")
                                            .replace("Gross Profit", "粗利益")
                                            .replace("Operating Income", "営業利益")
                                            .replace("Net Income", "純利益"),
                                            line=dict(width=3),
                                            marker=dict(size=10),
                                        )
                                    )

                                fig_pl.update_layout(
                                    title="損益推移（億円）",
                                    xaxis_title="年度",
                                    yaxis_title="金額（億円）",
                                    height=400,
                                    hovermode="x unified",
                                )
                                st.plotly_chart(fig_pl, width="stretch")

                        with pl_col2:
                            # 利益率の推移
                            if "Total Revenue" in income_stmt.index:
                                revenue = income_stmt.loc["Total Revenue"]
                                fig_margin = go.Figure()

                                margin_items = {
                                    "Gross Profit": "粗利益率",
                                    "Operating Income": "営業利益率",
                                    "Net Income": "純利益率",
                                }

                                for item, label in margin_items.items():
                                    if item in income_stmt.index:
                                        margin = (income_stmt.loc[item] / revenue * 100).dropna()
                                        dates = [
                                            d.strftime("%Y") if hasattr(d, "strftime") else str(d) for d in margin.index
                                        ]

                                        fig_margin.add_trace(
                                            go.Scatter(
                                                x=dates,
                                                y=margin.values,
                                                mode="lines+markers",
                                                name=label,
                                                line=dict(width=3),
                                                marker=dict(size=10),
                                            )
                                        )

                                # 業界平均の参考線を追加
                                if len(dates) > 0:
                                    # 営業利益率の参考値: 業界データがあれば使用、なければ日経平均
                                    ref_label = "営業利益率(業界平均)" if industry_data else "営業利益率(日経平均参考)"
                                    fig_margin.add_trace(
                                        go.Scatter(
                                            x=[dates[0], dates[-1]],
                                            y=[8.0, 8.0],
                                            mode="lines",
                                            name=ref_label,
                                            line=dict(width=2, dash="dash", color="rgba(255, 152, 0, 0.7)"),
                                            showlegend=True,
                                        )
                                    )

                                fig_margin.update_layout(
                                    title="利益率の推移（業界平均比較）" if industry_data else "利益率の推移（日経平均参考）",
                                    xaxis_title="年度",
                                    yaxis_title="利益率 (%)",
                                    height=400,
                                    hovermode="x unified",
                                )
                                st.plotly_chart(fig_margin, width="stretch")

                        # 営業費用の分析
                        st.write("#### 営業費用の内訳")
                        expense_items = [
                            "Cost Of Revenue",
                            "Operating Expense",
                            "Research And Development",
                            "Selling General And Administration",
                        ]
                        available_exp = [item for item in expense_items if item in income_stmt.index]

                        if available_exp:
                            fig_expense = go.Figure()

                            for item in available_exp:
                                values = income_stmt.loc[item].values / 1e8
                                dates = [
                                    d.strftime("%Y") if hasattr(d, "strftime") else str(d) for d in income_stmt.columns
                                ]

                                fig_expense.add_trace(
                                    go.Bar(
                                        x=dates,
                                        y=values,
                                        name=item.replace("Cost Of Revenue", "売上原価")
                                        .replace("Operating Expense", "営業費用")
                                        .replace("Research And Development", "研究開発費")
                                        .replace("Selling General And Administration", "販売管理費"),
                                        text=[f"{v:.0f}" for v in values],
                                        textposition="auto",
                                    )
                                )

                            fig_expense.update_layout(
                                title="営業費用の推移（億円）",
                                xaxis_title="年度",
                                yaxis_title="金額（億円）",
                                height=400,
                                barmode="stack",
                            )
                            st.plotly_chart(fig_expense, width="stretch")

                # === 貸借対照表タブ ===
                with fin_tab2:
                    if not balance_sheet.empty:
                        st.write("#### 資産・負債・純資産の推移")

                        bs_col1, bs_col2 = st.columns(2)

                        with bs_col1:
                            # 主要項目の推移
                            balance_items = [
                                "Total Assets",
                                "Total Liabilities Net Minority Interest",
                                "Stockholders Equity",
                            ]
                            available_balance = [item for item in balance_items if item in balance_sheet.index]

                            if available_balance:
                                fig_balance = go.Figure()

                                for item in available_balance:
                                    values = balance_sheet.loc[item].values / 1e8
                                    dates = [
                                        d.strftime("%Y") if hasattr(d, "strftime") else str(d)
                                        for d in balance_sheet.columns
                                    ]

                                    fig_balance.add_trace(
                                        go.Scatter(
                                            x=dates,
                                            y=values,
                                            mode="lines+markers",
                                            name=item.replace("Total Assets", "総資産")
                                            .replace("Total Liabilities Net Minority Interest", "総負債")
                                            .replace("Stockholders Equity", "株主資本"),
                                            line=dict(width=3),
                                            marker=dict(size=10),
                                        )
                                    )

                                fig_balance.update_layout(
                                    title="貸借対照表の推移（億円）",
                                    xaxis_title="年度",
                                    yaxis_title="金額（億円）",
                                    height=400,
                                    hovermode="x unified",
                                )
                                st.plotly_chart(fig_balance, width="stretch")

                        with bs_col2:
                            # 自己資本比率の推移
                            if "Stockholders Equity" in balance_sheet.index and "Total Assets" in balance_sheet.index:
                                equity_ratio = (
                                    balance_sheet.loc["Stockholders Equity"] / balance_sheet.loc["Total Assets"] * 100
                                ).dropna()
                                dates = [
                                    d.strftime("%Y") if hasattr(d, "strftime") else str(d) for d in equity_ratio.index
                                ]

                                fig_equity_ratio = go.Figure()

                                fig_equity_ratio.add_trace(
                                    go.Scatter(
                                        x=dates,
                                        y=equity_ratio.values,
                                        mode="lines+markers",
                                        name="自己資本比率",
                                        line=dict(width=4, color="#2962ff"),
                                        marker=dict(size=12),
                                        fill="tozeroy",
                                        fillcolor="rgba(41, 98, 255, 0.1)",
                                    )
                                )

                                # 参考線（45%）
                                if len(dates) > 0:
                                    ref_label = "参考値(業界平均)" if industry_data else "参考値(日経平均)"
                                    fig_equity_ratio.add_trace(
                                        go.Scatter(
                                            x=[dates[0], dates[-1]],
                                            y=[45.0, 45.0],
                                            mode="lines",
                                            name=ref_label,
                                            line=dict(width=2, dash="dash", color="rgba(255, 152, 0, 0.7)"),
                                            showlegend=True,
                                        )
                                    )

                                fig_equity_ratio.update_layout(
                                    title="自己資本比率の推移（業界平均比較）" if industry_data else "自己資本比率の推移（日経平均参考）",
                                    xaxis_title="年度",
                                    yaxis_title="自己資本比率 (%)",
                                    height=400,
                                )
                                st.plotly_chart(fig_equity_ratio, width="stretch")

                        # 資産の内訳
                        st.write("#### 資産の内訳")
                        asset_items = ["Current Assets", "Total Non Current Assets"]
                        available_assets = [item for item in asset_items if item in balance_sheet.index]

                        if available_assets:
                            fig_assets = go.Figure()

                            for item in available_assets:
                                values = balance_sheet.loc[item].values / 1e8
                                dates = [
                                    d.strftime("%Y") if hasattr(d, "strftime") else str(d)
                                    for d in balance_sheet.columns
                                ]

                                fig_assets.add_trace(
                                    go.Bar(
                                        x=dates,
                                        y=values,
                                        name=item.replace("Current Assets", "流動資産").replace(
                                            "Total Non Current Assets", "固定資産"
                                        ),
                                        text=[f"{v:.0f}" for v in values],
                                        textposition="auto",
                                    )
                                )

                            fig_assets.update_layout(
                                title="資産の内訳（億円）",
                                xaxis_title="年度",
                                yaxis_title="金額（億円）",
                                height=400,
                                barmode="stack",
                            )
                            st.plotly_chart(fig_assets, width="stretch")

                # === キャッシュフロータブ ===
                with fin_tab3:
                    if not cashflow_stmt.empty:
                        st.write("#### キャッシュフローの推移")

                        cf_items = ["Operating Cash Flow", "Investing Cash Flow", "Financing Cash Flow"]
                        available_cf = [item for item in cf_items if item in cashflow_stmt.index]

                        if available_cf:
                            fig_cf = go.Figure()

                            colors = {
                                "Operating Cash Flow": "#26a69a",
                                "Investing Cash Flow": "#ef5350",
                                "Financing Cash Flow": "#ffa726",
                            }

                            for item in available_cf:
                                values = cashflow_stmt.loc[item].values / 1e8
                                dates = [
                                    d.strftime("%Y") if hasattr(d, "strftime") else str(d)
                                    for d in cashflow_stmt.columns
                                ]

                                fig_cf.add_trace(
                                    go.Bar(
                                        x=dates,
                                        y=values,
                                        name=item.replace("Operating Cash Flow", "営業CF")
                                        .replace("Investing Cash Flow", "投資CF")
                                        .replace("Financing Cash Flow", "財務CF"),
                                        marker_color=colors.get(item, "#999999"),
                                        text=[f"{v:.0f}" for v in values],
                                        textposition="outside",
                                    )
                                )

                            fig_cf.update_layout(
                                title="キャッシュフローの推移（億円）",
                                xaxis_title="年度",
                                yaxis_title="金額（億円）",
                                height=450,
                                barmode="group",
                                hovermode="x unified",
                            )
                            st.plotly_chart(fig_cf, width="stretch")

                        # フリーキャッシュフロー
                        if "Free Cash Flow" in cashflow_stmt.index:
                            st.write("#### フリーキャッシュフロー")
                            fcf = cashflow_stmt.loc["Free Cash Flow"] / 1e8
                            dates = [d.strftime("%Y") if hasattr(d, "strftime") else str(d) for d in fcf.index]

                            fig_fcf = go.Figure()

                            fig_fcf.add_trace(
                                go.Bar(
                                    x=dates,
                                    y=fcf.values,
                                    name="フリーCF",
                                    marker_color=["#26a69a" if v > 0 else "#ef5350" for v in fcf.values],
                                    text=[f"{v:.0f}" for v in fcf.values],
                                    textposition="outside",
                                )
                            )

                            fig_fcf.update_layout(
                                title="フリーキャッシュフローの推移（億円）",
                                xaxis_title="年度",
                                yaxis_title="金額（億円）",
                                height=400,
                            )
                            st.plotly_chart(fig_fcf, width="stretch")

                # === 財務比率タブ ===
                with fin_tab4:
                    st.write("#### 主要財務比率の推移")

                    ratio_col1, ratio_col2 = st.columns(2)

                    with ratio_col1:
                        # ROE・ROAの推移
                        if not income_stmt.empty and not balance_sheet.empty:
                            if "Net Income" in income_stmt.index and "Stockholders Equity" in balance_sheet.index:
                                # データを年度で揃える
                                common_dates = income_stmt.columns.intersection(balance_sheet.columns)

                                if len(common_dates) > 0:
                                    net_income = income_stmt.loc["Net Income", common_dates]
                                    equity = balance_sheet.loc["Stockholders Equity", common_dates]
                                    roe = (net_income / equity * 100).dropna()

                                    fig_roe = go.Figure()
                                    dates = [d.strftime("%Y") if hasattr(d, "strftime") else str(d) for d in roe.index]

                                    fig_roe.add_trace(
                                        go.Scatter(
                                            x=dates,
                                            y=roe.values,
                                            mode="lines+markers",
                                            name="ROE",
                                            line=dict(width=4, color="#2962ff"),
                                            marker=dict(size=12),
                                            fill="tozeroy",
                                        )
                                    )

                                    if "Total Assets" in balance_sheet.index:
                                        assets = balance_sheet.loc["Total Assets", common_dates]
                                        roa = (net_income / assets * 100).dropna()

                                        fig_roe.add_trace(
                                            go.Scatter(
                                                x=[
                                                    d.strftime("%Y") if hasattr(d, "strftime") else str(d)
                                                    for d in roa.index
                                                ],
                                                y=roa.values,
                                                mode="lines+markers",
                                                name="ROA",
                                                line=dict(width=4, color="#26a69a"),
                                                marker=dict(size=12),
                                            )
                                        )

                                    # 参考線を追加
                                    if len(dates) > 0:
                                        roe_ref_label = "ROE(業界平均)" if industry_data else "ROE(日経平均参考)"
                                        roa_ref_label = "ROA(業界平均)" if industry_data else "ROA(日経平均参考)"
                                        
                                        fig_roe.add_trace(
                                            go.Scatter(
                                                x=[dates[0], dates[-1]],
                                                y=[9.5, 9.5],
                                                mode="lines",
                                                name=roe_ref_label,
                                                line=dict(width=2, dash="dash", color="rgba(255, 152, 0, 0.7)"),
                                                showlegend=True,
                                            )
                                        )
                                        fig_roe.add_trace(
                                            go.Scatter(
                                                x=[dates[0], dates[-1]],
                                                y=[5.0, 5.0],
                                                mode="lines",
                                                name=roa_ref_label,
                                                line=dict(width=2, dash="dot", color="rgba(255, 152, 0, 0.5)"),
                                                showlegend=True,
                                            )
                                        )

                                    fig_roe.update_layout(
                                        title="ROE・ROAの推移（業界平均比較）" if industry_data else "ROE・ROAの推移（日経平均参考）",
                                        xaxis_title="年度",
                                        yaxis_title="比率 (%)",
                                        height=400,
                                    )
                                    st.plotly_chart(fig_roe, width="stretch")

                    with ratio_col2:
                        # 負債比率の推移
                        if not balance_sheet.empty:
                            if (
                                "Total Liabilities Net Minority Interest" in balance_sheet.index
                                and "Stockholders Equity" in balance_sheet.index
                            ):
                                liabilities = balance_sheet.loc["Total Liabilities Net Minority Interest"]
                                equity = balance_sheet.loc["Stockholders Equity"]
                                debt_ratio = (liabilities / equity * 100).dropna()

                                dates = [
                                    d.strftime("%Y") if hasattr(d, "strftime") else str(d) for d in debt_ratio.index
                                ]

                                fig_debt = go.Figure()

                                fig_debt.add_trace(
                                    go.Scatter(
                                        x=dates,
                                        y=debt_ratio.values,
                                        mode="lines+markers",
                                        name="負債比率",
                                        line=dict(width=4, color="#ef5350"),
                                        marker=dict(size=12),
                                        fill="tozeroy",
                                        fillcolor="rgba(239, 83, 80, 0.1)",
                                    )
                                )

                                fig_debt.update_layout(
                                    title="負債比率の推移", xaxis_title="年度", yaxis_title="負債比率 (%)", height=400
                                )
                                st.plotly_chart(fig_debt, width="stretch")

        except Exception as e:
            st.info(f"💡 財務情報: この銘柄の財務データは利用できません")

    else:
        st.info("👈 サイドバーの「チャート更新」ボタンをクリックしてデータを取得してください")

# バックテスト実行
elif BACKTEST_ENABLED and st.session_state.run_backtest:
    st.header("🚀 バックテスト実行中...")

    detailed_mode = st.session_state.get("detailed_mode", False)

    if detailed_mode:
        st.info("📊 詳細モード: 全パラメータ組み合わせを検証します（数分かかる場合があります）")

    with st.spinner("バックテストを実行しています..."):
        try:
            indicators_config = {
                "ema": optimize_ema,
                "bb": optimize_bb,
                "ichimoku": optimize_ichimoku,
                "rsi": optimize_rsi,
                "macd": optimize_macd,
            }

            results, detailed_results = run_backtest_analysis(
                bt_product_code, bt_period, bt_duration, indicators_config, detailed=detailed_mode
            )

            st.success("✅ バックテスト完了！")

            if detailed_mode and detailed_results:
                st.success(f"📁 詳細結果がCSVファイルとして保存されました: {BACKTEST_DETAILS_DIR} フォルダ")

            st.session_state.show_backtest = True
            st.session_state.run_backtest = False
            st.session_state.backtest_detailed = detailed_results
            st.rerun()

        except Exception as e:
            st.error(f"❌ エラーが発生しました: {e}")
            import traceback

            st.code(traceback.format_exc())
            st.session_state.run_backtest = False

# 複数銘柄比較
elif st.session_state.run_compare:
    st.header("📊 銘柄比較")

    codes = [code.strip() for code in compare_codes.split("\n") if code.strip()]

    if len(codes) < 2:
        st.warning("⚠️ 比較には2つ以上の銘柄コードが必要です")
        st.session_state.run_compare = False
    else:
        with st.spinner(f"{len(codes)}銘柄のデータを取得中..."):
            comparison_data = {}

            for code in codes:
                df = load_chart_data(code, compare_period, compare_duration)
                if df is not None:
                    comparison_data[code] = df
                else:
                    st.warning(f"⚠️ {code}: データ取得に失敗しました")

            if len(comparison_data) >= 2:
                # 比較チャート作成
                fig = go.Figure()

                for code, df in comparison_data.items():
                    if normalize:
                        # 正規化（開始時点を100とする）
                        normalized = (df["close"] / df["close"].iloc[0]) * 100
                        y_data = normalized
                        y_label = "正規化価格（開始=100）"
                    else:
                        y_data = df["close"]
                        y_label = "価格"

                    fig.add_trace(go.Scatter(x=df["time"], y=y_data, name=code, mode="lines", line=dict(width=2)))

                fig.update_layout(
                    title="銘柄比較チャート",
                    xaxis_title="時刻",
                    yaxis_title=y_label,
                    height=600,
                    template="plotly_dark",
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )

                st.plotly_chart(fig, width="stretch")

                # パフォーマンス統計
                st.divider()
                st.subheader("📈 パフォーマンス比較")

                perf_data = []
                for code, df in comparison_data.items():
                    start_price = df["close"].iloc[0]
                    end_price = df["close"].iloc[-1]
                    change = end_price - start_price
                    change_pct = (change / start_price) * 100

                    perf_data.append(
                        {
                            "銘柄": code,
                            "開始価格": f"{start_price:.2f}",
                            "終了価格": f"{end_price:.2f}",
                            "変化額": f"{change:.2f}",
                            "変化率 (%)": f"{change_pct:+.2f}",
                        }
                    )

                perf_df = pd.DataFrame(perf_data)
                st.dataframe(perf_df, width="stretch", hide_index=True)

            else:
                st.error("❌ データを取得できた銘柄が2つ未満です")

        st.session_state.run_compare = False

else:
    st.warning("kabusapiは現在未実装です。Yahoo Financeをご利用ください。")

# バックテスト結果表示
if BACKTEST_ENABLED and st.session_state.show_backtest:
    st.divider()
    st.header("🎯 バックテスト結果")

    results = load_backtest_results()

    if results:
        # 基本情報
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("銘柄", results["product_code"])
        with col2:
            st.metric("期間", f"{results['period_days']}日")
        with col3:
            st.metric("時間軸", results["duration"])
        with col4:
            timestamp = datetime.fromisoformat(results["timestamp"].replace("Z", "+00:00"))
            st.metric("実行日時", timestamp.strftime("%Y-%m-%d %H:%M"))

        # パフォーマンス比較
        if "results" in results:
            st.subheader("� 指標別パフォーマンス")

            perf_data = []
            res = results["results"]

            if "ema" in res and "performance" in res["ema"]:
                perf_data.append(
                    {
                        "指標": "EMA",
                        "パフォーマンス (%)": res["ema"]["performance"],
                        "パラメータ": f"期間: {res['ema'].get('period1', res['ema'].get('period_1', 'N/A'))}, {res['ema'].get('period2', res['ema'].get('period_2', 'N/A'))}",
                    }
                )
            if "bollinger_bands" in res and "performance" in res["bollinger_bands"]:
                perf_data.append(
                    {
                        "指標": "Bollinger Bands",
                        "パフォーマンス (%)": res["bollinger_bands"]["performance"],
                        "パラメータ": f"N={res['bollinger_bands']['n']}, K={res['bollinger_bands']['k']}",
                    }
                )
            if "ichimoku" in res and "performance" in res["ichimoku"]:
                perf_data.append(
                    {"指標": "一目均衡表", "パフォーマンス (%)": res["ichimoku"]["performance"], "パラメータ": "標準"}
                )
            if "rsi" in res and "performance" in res["rsi"]:
                perf_data.append(
                    {
                        "指標": "RSI",
                        "パフォーマンス (%)": res["rsi"]["performance"],
                        "パラメータ": f"期間={res['rsi']['period']}, 買={res['rsi'].get('buy_threshold', res['rsi'].get('buy_thread', 'N/A'))}, 売={res['rsi'].get('sell_threshold', res['rsi'].get('sell_thread', 'N/A'))}",
                    }
                )
            if "macd" in res and "performance" in res["macd"]:
                perf_data.append(
                    {
                        "指標": "MACD",
                        "パフォーマンス (%)": res["macd"]["performance"],
                        "パラメータ": f"Fast={res['macd']['fast_period']}, Slow={res['macd']['slow_period']}, Signal={res['macd']['signal_period']}",
                    }
                )

            if perf_data:
                perf_df = pd.DataFrame(perf_data)
                perf_df = perf_df.sort_values("パフォーマンス (%)", ascending=False)

                # 棒グラフ
                fig_perf = go.Figure(
                    data=[
                        go.Bar(
                            x=perf_df["指標"],
                            y=perf_df["パフォーマンス (%)"],
                            marker_color=["#26a69a" if p > 0 else "#ef5350" for p in perf_df["パフォーマンス (%)"]],
                            text=[f"{p:.2f}%" for p in perf_df["パフォーマンス (%)"]],
                            textposition="auto",
                        )
                    ]
                )

                fig_perf.update_layout(
                    title="各指標のパフォーマンス比較",
                    xaxis_title="指標",
                    yaxis_title="パフォーマンス (%)",
                    height=400,
                    template="plotly_dark",
                )

                st.plotly_chart(fig_perf, width="stretch")

                # テーブル表示
                st.dataframe(perf_df.style.format({"パフォーマンス (%)": "{:.2f}"}), width="stretch", hide_index=True)

        # 詳細結果の表示
        if results.get("detailed_results"):
            st.divider()
            st.subheader("📈 詳細最適化結果")

            detailed = results["detailed_results"]

            # タブで指標ごとに表示
            indicator_tabs = []
            indicator_data = []

            if "ema" in detailed and "all_results" in detailed["ema"]:
                indicator_tabs.append("EMA")
                indicator_data.append(("ema", detailed["ema"]))
            if "bollinger_bands" in detailed and "all_results" in detailed["bollinger_bands"]:
                indicator_tabs.append("Bollinger Bands")
                indicator_data.append(("bollinger_bands", detailed["bollinger_bands"]))
            if "rsi" in detailed and "all_results" in detailed["rsi"]:
                indicator_tabs.append("RSI")
                indicator_data.append(("rsi", detailed["rsi"]))
            if "macd" in detailed and "all_results" in detailed["macd"]:
                indicator_tabs.append("MACD")
                indicator_data.append(("macd", detailed["macd"]))

            if indicator_tabs:
                tabs = st.tabs(indicator_tabs)

                for tab, (indicator_name, indicator_result) in zip(tabs, indicator_data, strict=False):
                    with tab:
                        all_results = indicator_result["all_results"]
                        df_results = pd.DataFrame(all_results)
                        df_results = df_results.sort_values("performance", ascending=False)

                        # 統計情報
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("テスト組み合わせ数", len(df_results))
                        with col2:
                            st.metric("最高パフォーマンス", f"{df_results['performance'].max():.2f}%")
                        with col3:
                            st.metric("平均パフォーマンス", f"{df_results['performance'].mean():.2f}%")
                        with col4:
                            st.metric("標準偏差", f"{df_results['performance'].std():.2f}%")

                        # パフォーマンス分布
                        st.write("**パフォーマンス分布:**")
                        fig_hist = go.Figure(
                            data=[
                                go.Histogram(
                                    x=df_results["performance"], nbinsx=50, marker_color="#2962ff", opacity=0.7
                                )
                            ]
                        )
                        fig_hist.update_layout(
                            title="パフォーマンス分布",
                            xaxis_title="パフォーマンス (%)",
                            yaxis_title="頻度",
                            height=300,
                            template="plotly_dark",
                        )
                        st.plotly_chart(fig_hist, width="stretch")

                        # ヒートマップ（2Dパラメータの場合）
                        if (
                            indicator_name == "ema"
                            and "period1" in df_results.columns
                            and "period2" in df_results.columns
                        ):
                            st.write("**パラメータヒートマップ:**")
                            pivot_df = df_results.pivot_table(
                                values="performance", index="period2", columns="period1", aggfunc="mean"
                            )

                            fig_heatmap = go.Figure(
                                data=go.Heatmap(
                                    z=pivot_df.values,
                                    x=pivot_df.columns,
                                    y=pivot_df.index,
                                    colorscale="RdYlGn",
                                    colorbar=dict(title="パフォーマンス %"),
                                )
                            )
                            fig_heatmap.update_layout(
                                title="EMAパラメータ vs パフォーマンス",
                                xaxis_title="Period 1",
                                yaxis_title="Period 2",
                                height=500,
                                template="plotly_dark",
                            )
                            st.plotly_chart(fig_heatmap, width="stretch")

                        elif (
                            indicator_name == "bollinger_bands"
                            and "n" in df_results.columns
                            and "k" in df_results.columns
                        ):
                            st.write("**パラメータヒートマップ:**")
                            pivot_df = df_results.pivot_table(
                                values="performance", index="k", columns="n", aggfunc="mean"
                            )

                            fig_heatmap = go.Figure(
                                data=go.Heatmap(
                                    z=pivot_df.values,
                                    x=pivot_df.columns,
                                    y=pivot_df.index,
                                    colorscale="RdYlGn",
                                    colorbar=dict(title="パフォーマンス %"),
                                )
                            )
                            fig_heatmap.update_layout(
                                title="Bollinger Bandsパラメータ vs パフォーマンス",
                                xaxis_title="N (期間)",
                                yaxis_title="K (標準偏差)",
                                height=500,
                                template="plotly_dark",
                            )
                            st.plotly_chart(fig_heatmap, width="stretch")

                        # Top 20結果
                        st.write("**Top 20 パラメータ組み合わせ:**")
                        top_results = df_results.head(20).copy()
                        top_results["順位"] = range(1, len(top_results) + 1)

                        # カラム順を調整
                        cols_order = (
                            ["順位"]
                            + [c for c in top_results.columns if c not in ["順位", "performance"]]
                            + ["performance"]
                        )
                        top_results = top_results[cols_order]

                        st.dataframe(
                            top_results.style.format({"performance": "{:.2f}%"}), width="stretch", hide_index=True
                        )

                        # CSV ダウンロード
                        csv_data = df_results.to_csv(index=False, encoding="utf-8-sig")
                        st.download_button(
                            label=f"📥 全{len(df_results)}件の結果をCSVダウンロード",
                            data=csv_data,
                            file_name=f"{results['product_code']}_{indicator_name}_results.csv",
                            mime="text/csv",
                        )

    else:
        st.error("バックテスト結果が見つかりません。バックテストを実行してください。")

    if st.button("結果を非表示"):
        st.session_state.show_backtest = False
        st.rerun()

# 詳細分析表示（新機能）
if BACKTEST_ENABLED and st.session_state.show_enhanced and ENHANCED_BACKTEST_AVAILABLE:
    st.divider()
    st.header("📈 詳細パフォーマンス分析")
    
    results = load_backtest_results()
    
    if results and 'detailed_results' in results:
        tab1, tab2, tab3, tab4 = st.tabs(["📊 総合メトリクス", "📉 パラメータ分析", "🎯 戦略比較", "📋 詳細データ"])
        
        with tab1:
            st.subheader("総合パフォーマンス指標")
            
            # 各戦略のベストパフォーマンスを収集
            all_perfs = []
            for strategy in ['ema', 'bollinger_bands', 'rsi', 'macd']:
                if strategy in results.get('detailed_results', {}):
                    perf = results['detailed_results'][strategy].get('best_performance', 0)
                    all_perfs.append(perf)
            
            if all_perfs:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("最高パフォーマンス", f"{max(all_perfs):.2f}%")
                with col2:
                    st.metric("平均パフォーマンス", f"{np.mean(all_perfs):.2f}%")
                with col3:
                    st.metric("最低パフォーマンス", f"{min(all_perfs):.2f}%")
                with col4:
                    profitable = sum(1 for p in all_perfs if p > 0)
                    st.metric("利益戦略数", f"{profitable}/{len(all_perfs)}")
                
                # 戦略別パフォーマンス比較
                st.subheader("戦略別パフォーマンス")
                strategy_names = {
                    'ema': 'EMA',
                    'bollinger_bands': 'Bollinger Bands',
                    'rsi': 'RSI',
                    'macd': 'MACD',
                    'ichimoku': 'Ichimoku'
                }
                
                strategy_data = []
                for strategy, display_name in strategy_names.items():
                    if strategy in results.get('results', {}):
                        perf = results['results'][strategy].get('performance', 0)
                        strategy_data.append({
                            '戦略': display_name,
                            'パフォーマンス': perf,
                            '状態': '✅ 利益' if perf > 0 else '❌ 損失'
                        })
                
                if strategy_data:
                    df_strategies = pd.DataFrame(strategy_data)
                    df_strategies = df_strategies.sort_values('パフォーマンス', ascending=False)
                    
                    fig_strategies = go.Figure(data=[
                        go.Bar(
                            x=df_strategies['戦略'],
                            y=df_strategies['パフォーマンス'],
                            marker_color=['green' if p > 0 else 'red' for p in df_strategies['パフォーマンス']],
                            text=df_strategies['パフォーマンス'].apply(lambda x: f"{x:.2f}%"),
                            textposition='auto',
                        )
                    ])
                    
                    fig_strategies.update_layout(
                        title='戦略別パフォーマンス比較',
                        xaxis_title='戦略',
                        yaxis_title='パフォーマンス (%)',
                        height=400,
                        template='plotly_dark'
                    )
                    
                    st.plotly_chart(fig_strategies, use_container_width=True)
                    st.dataframe(df_strategies, use_container_width=True, hide_index=True)
        
        with tab2:
            st.subheader("パラメータ最適化詳細")
            
            selected_strategy = st.selectbox(
                "戦略を選択",
                ['EMA', 'Bollinger Bands', 'RSI', 'MACD'],
                key='param_strategy'
            )
            
            strategy_map = {
                'EMA': 'ema',
                'Bollinger Bands': 'bollinger_bands',
                'RSI': 'rsi',
                'MACD': 'macd'
            }
            
            strategy_key = strategy_map[selected_strategy]
            
            if strategy_key in results.get('detailed_results', {}):
                detail = results['detailed_results'][strategy_key]
                
                # ベストパラメータ表示
                st.info(f"**最高パフォーマンス: {detail.get('best_performance', 0):.2f}%**")
                
                if 'best_params' in detail:
                    st.write("**最適パラメータ:**")
                    params_df = pd.DataFrame([detail['best_params']])
                    st.dataframe(params_df, use_container_width=True, hide_index=True)
                
                # パラメータ分布
                if 'all_results' in detail and detail['all_results']:
                    all_results = detail['all_results']
                    perfs = [r['performance'] for r in all_results]
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("テスト組み合わせ数", len(all_results))
                    with col2:
                        positive = sum(1 for p in perfs if p > 0)
                        st.metric("利益パラメータ数", f"{positive} ({positive/len(perfs)*100:.1f}%)")
                    with col3:
                        st.metric("パフォーマンス範囲", f"{min(perfs):.1f}% ~ {max(perfs):.1f}%")
                    
                    # パフォーマンス分布ヒストグラム
                    fig_dist = go.Figure(data=[
                        go.Histogram(
                            x=perfs,
                            nbinsx=50,
                            marker_color='#2962ff',
                            opacity=0.7
                        )
                    ])
                    
                    fig_dist.update_layout(
                        title='パフォーマンス分布',
                        xaxis_title='パフォーマンス (%)',
                        yaxis_title='頻度',
                        height=400,
                        template='plotly_dark'
                    )
                    
                    st.plotly_chart(fig_dist, use_container_width=True)
                    
                    # トップ10とボトム10を表示
                    df_all = pd.DataFrame(all_results)
                    df_all = df_all.sort_values('performance', ascending=False)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**トップ10パラメータ**")
                        st.dataframe(df_all.head(10), use_container_width=True, hide_index=True)
                    with col2:
                        st.write("**ボトム10パラメータ**")
                        st.dataframe(df_all.tail(10), use_container_width=True, hide_index=True)
        
        with tab3:
            st.subheader("戦略比較分析")
            
            # 各戦略のパフォーマンス分布を比較
            comparison_data = {}
            
            for strategy in ['ema', 'bollinger_bands', 'rsi', 'macd']:
                if strategy in results.get('detailed_results', {}):
                    detail = results['detailed_results'][strategy]
                    if 'all_results' in detail and detail['all_results']:
                        perfs = [r['performance'] for r in detail['all_results']]
                        comparison_data[strategy] = perfs
            
            if comparison_data:
                # ボックスプロット
                fig_box = go.Figure()
                
                strategy_names = {
                    'ema': 'EMA',
                    'bollinger_bands': 'Bollinger Bands',
                    'rsi': 'RSI',
                    'macd': 'MACD'
                }
                
                for strategy, perfs in comparison_data.items():
                    fig_box.add_trace(go.Box(
                        y=perfs,
                        name=strategy_names.get(strategy, strategy),
                        boxmean='sd'
                    ))
                
                fig_box.update_layout(
                    title='戦略別パフォーマンス分布（ボックスプロット）',
                    yaxis_title='パフォーマンス (%)',
                    height=500,
                    template='plotly_dark'
                )
                
                st.plotly_chart(fig_box, use_container_width=True)
                
                # 統計サマリー
                st.subheader("統計サマリー")
                summary_data = []
                
                for strategy, perfs in comparison_data.items():
                    summary_data.append({
                        '戦略': strategy_names.get(strategy, strategy),
                        '平均': np.mean(perfs),
                        '中央値': np.median(perfs),
                        '最大': max(perfs),
                        '最小': min(perfs),
                        '標準偏差': np.std(perfs),
                        '利益確率': f"{sum(1 for p in perfs if p > 0) / len(perfs) * 100:.1f}%"
                    })
                
                df_summary = pd.DataFrame(summary_data)
                df_summary = df_summary.sort_values('平均', ascending=False)
                
                # 数値列をフォーマット
                for col in ['平均', '中央値', '最大', '最小', '標準偏差']:
                    df_summary[col] = df_summary[col].apply(lambda x: f"{x:.2f}")
                
                st.dataframe(df_summary, use_container_width=True, hide_index=True)
        
        with tab4:
            st.subheader("詳細データエクスポート")
            
            st.write("バックテスト結果の詳細データを確認できます。")
            
            # JSONデータを表示
            with st.expander("📋 完全なJSONデータを表示"):
                st.json(results)
            
            # CSVダウンロード
            st.write("**パラメータ詳細のダウンロード**")
            
            csv_files = []
            details_dir = BACKTEST_DETAILS_DIR if os.path.exists(BACKTEST_DETAILS_DIR) else 'backtest_details'
            if os.path.exists(details_dir):
                for file in os.listdir(details_dir):
                    if file.endswith('.csv') and results['product_code'] in file:
                        csv_files.append(file)
            
            if csv_files:
                selected_csv = st.selectbox("CSVファイルを選択", csv_files)
                
                if selected_csv:
                    csv_path = os.path.join(details_dir, selected_csv)
                    df_csv = pd.read_csv(csv_path)
                    
                    st.write(f"**{selected_csv}** - {len(df_csv)} 件")
                    st.dataframe(df_csv, use_container_width=True)
                    
                    # ダウンロードボタン
                    csv_data = df_csv.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 CSVをダウンロード",
                        data=csv_data,
                        file_name=selected_csv,
                        mime='text/csv'
                    )
            else:
                st.info("詳細CSVファイルが見つかりません。`--detailed`オプションでバックテストを実行してください。")
    
    else:
        st.error("詳細バックテスト結果が見つかりません。`python backtest_yahoo.py --detailed`を実行してください。")
    
    if st.button("詳細分析を非表示"):
        st.session_state.show_enhanced = False
        st.rerun()

# フッター
st.divider()
st.markdown(
    """
<div style='text-align: center; color: #888;'>
    <p>kabucomtrading - Trading Dashboard with Yahoo Finance & Backtest Results</p>
</div>
""",
    unsafe_allow_html=True,
)
