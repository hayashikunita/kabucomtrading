# Improvement Issues

## Week 1: 壊れやすい箇所の修正と実装穴埋め

### 1) Strategy Lab の CSS 文字列混入を修正
- 状態: Done (2026-07-21)
- 内容:
  - strategy_lab.py の CSS ブロック内に混入していた Python 断片を削除。
  - 画面スタイルの崩れ・可読性低下リスクを解消。
- 対象ファイル:
  - strategy_lab.py

### 2) multi_stock_backtest の backtest_yahoo 依存を解消
- 状態: Done (2026-07-21)
- 内容:
  - scripts/multi_stock_backtest.py から存在しない backtest_yahoo 依存を削除。
  - StrategyEngine + compile_strategy + RiskManagement ベースの実行ロジックを内蔵し、互換的な results / detailed_results を返すように変更。
  - ranking 出力仕様は維持。
- 対象ファイル:
  - scripts/multi_stock_backtest.py

### 3) streamdata のリアルタイム取り込みを実装
- 状態: Done (2026-07-21)
- 内容:
  - app/controllers/streamdata.py に、kabusapi get_ticker を用いたポーリング取り込みを実装。
  - 例外時に指数バックオフして再試行する耐障害ロジックを追加。
  - ticker に product_code がない場合の補完、未対応 duration のスキップを追加して実行時エラーを回避。
- 対象ファイル:
  - app/controllers/streamdata.py

## Next Candidates (Week 2)
- pyproject.toml の type checking を段階的に有効化。
- docs/BACKTEST_GUIDE.md の旧 backtest_yahoo 記述を現実装へ更新。
- Strategy Lab / Streamlit UI のスモークテスト追加。
