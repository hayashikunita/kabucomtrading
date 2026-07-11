# 拡張バックテスト機能ガイド

バックテストシステムを大幅に強化しました。以下の新機能が追加されています。

## 📊 新機能一覧

### 1. 詳細パフォーマンス指標 (`backtest_metrics.py`)

シャープレシオ、最大ドローダウン、勝率など18種類以上の指標を計算します。

**主な指標:**
- 総利益 / 総取引数
- 勝率 / プロフィットファクター
- 最大ドローダウン
- シャープレシオ / ソルティノレシオ
- リカバリーファクター
- カルマーレシオ
- 最大連勝数 / 最大連敗数
- 期待値

**使用例:**
```python
from backtest_metrics import BacktestMetrics

trades = [
    {"profit": 100, "entry_price": 1000, ...},
    {"profit": -50, "entry_price": 1050, ...},
    # ...
]

metrics = BacktestMetrics(trades)
metrics.print_summary()

# すべての指標を辞書で取得
all_metrics = metrics.get_all_metrics(initial_capital=1000000, years=1.0)
```

### 2. 取引ログ記録 (`trade_logger.py`)

すべての取引を詳細に記録し、CSV/JSON形式で保存できます。

**記録される情報:**
- エントリー/イグジット時刻
- エントリー/イグジット価格
- 損益 / 損益率
- 保有期間
- 使用戦略
- 指標値（エントリー時/イグジット時）

**使用例:**
```python
from trade_logger import TradeLogger

logger = TradeLogger()

# ポジションオープン
logger.open_position(
    time=datetime.now(),
    price=1000,
    side="BUY",
    quantity=100,
    strategy="EMA",
    indicator_values={"ema_short": 990, "ema_long": 980}
)

# ポジションクローズ
logger.close_position(
    time=datetime.now(),
    price=1050,
    indicator_values={"ema_short": 1040, "ema_long": 1020}
)

# 保存
logger.save_to_csv("trades.csv")
logger.save_to_json("trades.json")
```

### 3. 結果可視化 (`backtest_visualizer.py`)

matplotlib/seabornを使った豊富なグラフを自動生成します。

**生成されるグラフ:**
- 資産曲線 (Equity Curve)
- ドローダウンチャート
- 損益分布ヒストグラム
- 月次リターン
- パラメータ最適化ヒートマップ

**使用例:**
```python
from backtest_visualizer import BacktestVisualizer

visualizer = BacktestVisualizer(trades)

# 個別グラフ生成
visualizer.plot_equity_curve(save_path="equity.png")
visualizer.plot_drawdown(save_path="drawdown.png")
visualizer.plot_profit_distribution(save_path="profit_dist.png")
visualizer.plot_monthly_returns(save_path="monthly.png")

# 包括レポート生成（すべてのグラフを一括生成）
visualizer.create_comprehensive_report(output_dir="reports", prefix="backtest")
```

### 4. 複数銘柄バックテスト (`multi_stock_backtest.py`)

複数の銘柄を一括でバックテストし、ランキング形式で比較できます。

**特徴:**
- 並列処理対応（高速）
- 戦略別ランキング生成
- CSV出力対応

**使用例:**
```bash
# 複数銘柄をバックテスト
python multi_stock_backtest.py --codes 7203 9984 6758 --period 365 --parallel

# 詳細モード（全パラメータ組み合わせテスト）
python multi_stock_backtest.py --codes 7203 9984 6758 --detailed --parallel --workers 8
```

**Pythonコード例:**
```python
from multi_stock_backtest import MultiStockBacktest

codes = ["7203", "9984", "6758", "8306"]
backtest = MultiStockBacktest(
    product_codes=codes,
    period_days=365,
    duration="1d",
    max_workers=4
)

backtest.run_all(detailed=False, parallel=True)
backtest.print_summary()
backtest.save_results()
backtest.save_ranking_csv()
```

### 5. ウォークフォワード分析 (`walkforward_analysis.py`)

過学習を検証するため、訓練期間とテスト期間に分割してバックテストします。

**特徴:**
- データを複数期間に分割
- 訓練データで最適化 → テストデータで検証
- 劣化率の計算
- 安定性スコアの算出

**使用例:**
```bash
# ウォークフォワード分析
python walkforward_analysis.py --code 7203 --days 730 --train-ratio 0.7 --splits 3 --strategy ema

# パラメータ説明:
# --days: 総期間（日数）
# --train-ratio: 訓練データの割合（0.0-1.0）
# --splits: 分割数
# --strategy: ema, bb, rsi, macd
```

**Pythonコード例:**
```python
from walkforward_analysis import WalkForwardAnalysis

wf = WalkForwardAnalysis(
    product_code="7203",
    total_days=730,
    train_ratio=0.7,
    n_splits=3,
    duration="1d"
)

wf.run_analysis(strategy="ema")
wf.print_summary()
wf.save_results("results/walkforward/walkforward_results.json")
```

### 6. リスク管理機能 (`enhanced_backtest.py`)

実践的なリスク管理機能を備えた拡張バックテストエンジンです。

**機能:**
- ポジションサイズ管理
- ストップロス設定
- テイクプロフィット設定
- 最大同時保有ポジション数制限
- 1取引あたりの最大リスク設定

**使用例:**
```python
from enhanced_backtest import EnhancedBacktest, RiskManagement

# リスク管理設定
risk_mgmt = RiskManagement(
    initial_capital=1000000,
    position_size_percent=50.0,  # 資金の50%
    stop_loss_percent=2.0,       # 2%損失でストップロス
    take_profit_percent=5.0,     # 5%利益でテイクプロフィット
    max_positions=3,             # 最大3ポジション同時保有
    risk_per_trade_percent=2.0   # 1取引あたり2%リスク
)

# バックテスト実行
backtest = EnhancedBacktest(
    product_code="7203",
    candles=candle_data,
    risk_management=risk_mgmt
)

signals = [
    {"time": datetime(2024, 1, 1), "type": "BUY", "price": 1000, "indicators": {}},
    {"time": datetime(2024, 1, 5), "type": "SELL", "price": 1050, "indicators": {}},
    # ...
]

results = backtest.execute_backtest(signals)
backtest.print_summary()
backtest.save_results(output_dir="results", prefix="risk_managed")
```

## 🚀 統合使用例

既存の`backtest_yahoo.py`と組み合わせて使用できます:

```python
from backtest_yahoo import YahooBacktest
from backtest_metrics import BacktestMetrics
from backtest_visualizer import BacktestVisualizer

# 1. 通常のバックテスト実行
backtest = YahooBacktest("7203", 365, "1d")
backtest.run_backtest(detailed=True)

# 2. 詳細指標の計算（拡張版）
# TODO: 既存のバックテストに取引ログ機能を統合する必要があります
# trades = backtest.get_detailed_trades()  # 実装予定
# metrics = BacktestMetrics(trades)
# metrics.print_summary()

# 3. 可視化
# visualizer = BacktestVisualizer(trades)
# visualizer.create_comprehensive_report("reports")
```

## 📁 出力ファイル

各機能は以下のファイルを生成します:

### backtest_yahoo.py
- `results/backtest_results.json` - バックテスト結果
- `results/backtest_details/*.csv` - パラメータ詳細結果

### multi_stock_backtest.py
- `results/multi_stock_backtest_results.json` - 複数銘柄結果
- `results/backtest_rankings/*.csv` - 戦略別ランキング

### walkforward_analysis.py
- `results/walkforward/walkforward_*.json` - ウォークフォワード分析結果

### enhanced_backtest.py
- `*_trades_*.csv` - 取引ログ（CSV）
- `*_trades_*.json` - 取引ログ（JSON）
- `*_equity_curve.png` - 資産曲線
- `*_drawdown.png` - ドローダウンチャート
- `*_profit_distribution.png` - 損益分布
- `*_monthly_returns.png` - 月次リターン

## 🔧 必要なパッケージ

新機能を使用するには以下のパッケージが必要です:

```bash
pip install numpy pandas matplotlib seaborn
```

## 💡 ベストプラクティス

1. **最初は詳細モードで実行** - パラメータの挙動を理解する
2. **ウォークフォワード分析で検証** - 過学習を避ける
3. **複数銘柄で比較** - 最適な銘柄を見つける
4. **リスク管理を必ず設定** - 実践的なバックテスト
5. **結果を可視化** - グラフで直感的に理解

## 📝 次のステップ

既存の`backtest_yahoo.py`に以下の統合が推奨されます:

1. TradeLoggerの統合 - 取引詳細の記録
2. BacktestMetricsの統合 - 詳細指標の計算
3. BacktestVisualizerの統合 - 結果の可視化
4. RiskManagementの統合 - リスク管理機能

これにより、より実践的で詳細なバックテストが可能になります。
