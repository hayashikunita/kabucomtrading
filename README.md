# kabucomtrading

kabu.com証券のAPI（kabusapi）とYahoo Financeを活用した株式・ETF自動売買システムです。
テクニカル指標によるシグナル生成、バックテスト機能、**Streamlit**によるインタラクティブなデータ可視化を提供します。

## ⚠️ 注意事項

**本プロジェクトは現在開発中です。**
仕様や構成は予告なく変更される可能性があります。
実際の取引での使用は自己責任でお願いします。

## 機能

- **自動売買**: kabusapi経由での注文執行
- **テクニカル指標**: SMA, EMA, Bollinger Bands, Ichimoku Cloud, RSI, MACD
- **バックテスト**: 過去データを用いた戦略検証
- **パラメータ最適化**: 複数のテクニカル指標パラメータを自動最適化
  - **詳細モード**: 全パラメータ組み合わせの結果を出力・可視化
  - **CSV出力**: 全結果をスプレッドシートで分析可能
  - **ヒートマップ**: 2Dパラメータ空間での最適領域を視覚化
- **Yahoo Finance連携**: kabusapi接続なしで過去データを取得・分析
- **Streamlitダッシュボード**: インタラクティブなローソク足チャートとバックテスト結果の可視化
  - パフォーマンス分布ヒストグラム
  - パラメータヒートマップ
  - Top 20ランキング表示
  - CSVダウンロード機能
- **データ永続化**: SQLiteによる時系列データ・シグナル管理

## 必要要件

- Python 3.9以上（推奨: 3.12）
- kabu.com証券のAPIトークン（kabusapi使用時のみ）
- TA-Libライブラリ（事前にインストールが必要）

## インストール

### 1. リポジトリのクローン

```bash
git clone https://github.com/yourusername/kabucomtrading.git
cd kabucomtrading
```

### 2. TA-Libのインストール

#### Windows
[TA-Lib公式サイト](https://www.ta-lib.org/)からインストーラーをダウンロードしてインストール

#### macOS
```bash
brew install ta-lib
```

#### Linux
```bash
sudo apt-get install ta-lib
```

### 3. Pythonパッケージのインストール

```bash
uv sync
```

または

```bash
pip install -e .
```

## 設定

`settings.ini`ファイルを編集してAPIトークンや取引パラメータを設定します。

```ini
[kabusapi]
token = YOUR_API_TOKEN_HERE
password = YOUR_PASSWORD_HERE
url = https://localhost:18080/kabusapi
product_code = 1459

[db]
name = stockdata.sql
driver = sqlite3

[web]
port = 8080

[pytrading]
trade_duration = 1m
back_test = False
use_percent = 0.9
past_period = 365
stop_limit_percent = 0.9
num_ranking = 3
```

### 設定項目の説明

#### [kabusapi]
- `token`: kabusapiのAPIトークン
- `password`: 注文時のパスワード
- `url`: kabusapiのエンドポイントURL
- `product_code`: 取引対象の銘柄コード（例: 1459 = 楽天・全世界株式インデックス・ファンド）

#### [pytrading]
- `trade_duration`: ローソク足の時間軸（5s / 1m / 1h）
- `back_test`: バックテストモード（True / False）
- `use_percent`: 利用可能資金の使用割合（0.0～1.0）
- `past_period`: 過去データ取得期間（日数）
- `stop_limit_percent`: ストップロス割合（0.0～1.0）
- `num_ranking`: 使用するテクニカル指標の上位件数

## クイックスタート

### 1. 環境構築
```bash
# リポジトリをクローン
git clone https://github.com/yourusername/kabucomtrading.git
cd kabucomtrading

# 依存関係をインストール
uv sync
# または
pip install -e .
```

### 2. 設定ファイルの編集
`settings.ini`を編集して銘柄コードなどを設定

### 3. Streamlitアプリで可視化（推奨）
```bash
# 仮想環境のPythonでStreamlitを起動
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

ブラウザで http://localhost:8501 にアクセス

### 4. 詳細バックテストを実行
1. サイドバーの「🎯 バックテスト」タブを選択
2. 銘柄コード入力（例: 1459）
3. ✅ **「詳細モード」にチェック**
4. 「🚀 バックテスト実行」をクリック
5. 結果を確認・CSVダウンロード

## 使い方

### Streamlitダッシュボードの起動（推奨）

```bash
uv run streamlit run streamlit_app.py
```

または

```bash
streamlit run streamlit_app.py
```

ブラウザで自動的に開きます（デフォルト: http://localhost:8501）

#### Streamlitダッシュボードの機能

**サイドバー - 📊 チャートタブ:**
- **データソース選択**: Yahoo Finance / kabusapi
- **銘柄コード入力**: 日本株の証券コードを入力（例: 1459, 7203, 9984）
- **時間軸選択**: 1分足 / 1時間足 / 日足
- **期間設定**: 7〜730日の範囲でデータ取得期間を指定
- **テクニカル指標**: SMA, EMA, Bollinger Bands, 出来高表示
- **チャート高さ調整**: 300〜1200pxの範囲でチャートサイズを変更
- **チャート更新ボタン**: 設定を反映してチャートを再描画

**サイドバー - 🎯 バックテストタブ:**
- **銘柄・期間・時間軸設定**: バックテスト対象の指定
- **✅ 詳細モード**: 全パラメータ組み合わせの結果を出力
- **指標選択**: EMA, Bollinger Bands, 一目均衡表, RSI, MACD
- **バックテスト実行ボタン**: 最適化を実行
- **結果表示ボタン**: 保存済み結果を読み込み

**サイドバー - 📉 比較タブ:**
- **複数銘柄比較**: 最大10銘柄の価格推移を比較
- **正規化表示**: 開始時点を100として正規化
- **パフォーマンス統計**: 変化率などの比較表示

**メインエリア:**
- **統計情報カード**: データ数、最新価格、変化率、最高値を一目で確認
- **Plotlyインタラクティブチャート**:
  - ズーム・パン操作可能
  - ホバーで詳細情報表示
  - ダークテーマ対応
  - 出来高サブプロット
  - トレードシグナル表示（買い/売りマーカー）
- **バックテスト結果（詳細モード対応）**:
  - **指標別パフォーマンス比較**: 棒グラフで視覚化（緑=プラス、赤=マイナス）
  - **詳細結果タブ**: 指標ごとにタブ表示
    - 統計情報: テスト組み合わせ数、最高/平均/標準偏差
    - パフォーマンス分布ヒストグラム
    - パラメータヒートマップ（2Dパラメータ空間）
    - Top 20ランキングテーブル
    - 📥 CSVダウンロードボタン（全結果）

### 従来のFlask Webサーバ（レガシー）

```bash
python main.py
```

これにより以下が起動します：
- ストリーミングデータ取得スレッド
- Webサーバ（デフォルト: http://localhost:8081）

ブラウザで `http://localhost:8081` にアクセスすると、Lightweight Chartsを使用したチャートを確認できます。

### バックテストモード

`settings.ini` で `back_test = True` に設定すると、過去データでの戦略検証を行います。

### Yahoo Financeを使ったバックテスト

Yahoo Financeから過去の株価データを取得してバックテストを実行できます。
kabusapiへの接続なしで、過去データでの戦略検証が可能です。

#### 1. yfinanceのインストール

```bash
pip install yfinance
```

または、プロジェクト全体をインストール：

```bash
pip install -e .
```

#### 2. バックテスト実行

**標準モード（最適パラメータのみ）:**
```bash
python backtest_yahoo.py
```

**詳細モード（全パラメータ組み合わせを出力）:**
```bash
python backtest_yahoo.py --detailed
```

このスクリプトは以下を実行します：
1. Yahoo Financeから `settings.ini` で指定した銘柄の過去データを取得
2. 複数のテクニカル指標（EMA, Bollinger Bands, Ichimoku, RSI, MACD）でバックテスト
3. 各指標の最適パラメータを探索
4. 結果をコンソールに表示し、`backtest_results.json` に保存
5. **詳細モード**: 全パラメータの結果を `backtest_details/` フォルダにCSV形式で保存

#### 3. 詳細モードの特徴

詳細モードでは、すべてのパラメータ組み合わせの結果を出力します：

- **EMA**: 期間1（5-29）× 期間2（10-48）の全組み合わせ（約200-400パターン）
- **Bollinger Bands**: N（10-45）× K（1.0-3.0）の全組み合わせ（約40パターン）
- **RSI**: 期間（7-29）× 買閾値（20-35）× 売閾値（60-80）の全組み合わせ（約500パターン）
- **MACD**: Fast（8-14）× Slow（20-30）× Signal（5-11）の全組み合わせ（約100パターン）

出力ファイル例：
```
backtest_details/
  ├── 1459_ema_20240115_143022.csv
  ├── 1459_bollinger_bands_20240115_143022.csv
  ├── 1459_rsi_20240115_143022.csv
  └── 1459_macd_20240115_143022.csv
```

各CSVファイルには以下の情報が含まれます：
- パラメータ値（period1, period2, n, k, etc.）
- パフォーマンス（%）
- パフォーマンス順にソート済み

#### 4. Streamlitでの詳細結果表示

Streamlitダッシュボードで詳細モードのバックテストを実行すると：

1. **詳細モードチェックボックス**: サイドバーのバックテスト設定で有効化
2. **パフォーマンス分布ヒストグラム**: 全パラメータのパフォーマンス分布を可視化
3. **パラメータヒートマップ**: 2Dパラメータ空間での最適領域を視覚化
4. **Top 20ランキング**: 最高パフォーマンスのパラメータ組み合わせを表示
5. **CSVダウンロード**: 全結果をダウンロードして詳細分析可能
6. **統計情報**: テスト組み合わせ数、最高/平均/標準偏差

#### 5. 出力例

```
バックテスト結果サマリー
============================================================
銘柄コード: 1459
期間: 365日
時間軸: 1m
------------------------------------------------------------

EMA:
  パフォーマンス: 1250.50
  期間1: 7
  期間2: 14
  テスト済み組み合わせ数: 287

Bollinger Bands:
  パフォーマンス: 980.30
  N: 20
  K: 2.00
  テスト済み組み合わせ数: 40

RSI:
  パフォーマンス: 850.20
  期間: 14
  買いスレッド: 30.00
  売りスレッド: 70.00
  テスト済み組み合わせ数: 552

MACD:
  パフォーマンス: 1050.40
  Fast期間: 12
  Slow期間: 26
  Signal期間: 9
  テスト済み組み合わせ数: 96
============================================================

詳細結果は backtest_details/ フォルダに保存されました。
```

#### 6. Yahoo Financeデータの制限事項

- **1分足**: 最大7日間のデータのみ取得可能
- **5分足**: 最大60日間のデータのみ取得可能
- **1時間足/日足**: 長期間のデータ取得可能
- **5秒足**: Yahoo Financeは対応していないため、1分足で代用

#### 7. カスタマイズ

コマンドライン引数でカスタマイズできます：

```bash
# トヨタ自動車で詳細バックテスト実行
python backtest_yahoo.py --detailed --product-code 7203 --period 180 --duration 1d

# ソフトバンクグループで標準バックテスト
python backtest_yahoo.py --product-code 9984 --period 90 --duration 1h
```

利用可能な引数：
- `--detailed`: 詳細モードを有効化
- `--product-code CODE`: 銘柄コード（デフォルト: settings.iniから）
- `--period DAYS`: データ取得期間（日数）
- `--duration TIMEFRAME`: 時間軸（1m, 1h, 1d）

## アーキテクチャ

このプロジェクトは、以下のレイヤーで構成されています：

### システム構成図（Streamlit版）

```
┌─────────────────────────────────────────────────────────┐
│                 streamlit_app.py                        │
│           (Streamlitダッシュボード)                      │
│  - インタラクティブUI                                    │
│  - リアルタイムチャート更新                               │
│  - バックテスト結果可視化                                 │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
    ┌────────────────────┐
    │  Yahoo Finance     │
    │  Data Fetcher      │
    │  (yahoo.py)        │
    └────────┬───────────┘
             │
             ▼
    ┌────────────────────┐        ┌────────────────────┐
    │  DataFrameCandle   │        │  Backtest Results  │
    │  (dfcandle.py)     │◄───────┤  (JSON)            │
    │  - 指標計算         │        │  - パラメータ       │
    │  - バックテスト     │        │  - パフォーマンス   │
    └────────────────────┘        └────────────────────┘
```

### システム構成図（レガシーFlask版）

```
┌─────────────────────────────────────────────────────────┐
│                     main.py                             │
│              (エントリーポイント)                         │
└────────────┬──────────────────────────┬─────────────────┘
             │                          │
             ▼                          ▼
    ┌─────────────────┐        ┌─────────────────┐
    │  StreamData     │        │  WebServer      │
    │  (データ収集)    │        │  (Flask API)    │
    └────────┬────────┘        └────────┬────────┘
             │                          │
             ▼                          ▼
    ┌─────────────────┐        ┌─────────────────┐
    │  AI Trading     │        │  Chart View     │
    │  (売買判断)      │◄───────┤  (可視化)       │
    └────────┬────────┘        └─────────────────┘
             │
             ▼
    ┌─────────────────┐
    │  KabusApiClient │
    │  (API通信)       │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐        ┌─────────────────┐
    │  Candle Models  │        │  Signal Events  │
    │  (データ永続化)  │        │  (シグナル記録)  │
    └─────────────────┘        └─────────────────┘
```

### データフロー（Streamlit版）

1. **ユーザー操作**: Streamlit UI → 銘柄コード・時間軸・期間を選択
2. **データ取得**: `yahoo.py` → Yahoo Finance APIから過去データ取得
3. **データ変換**: pandas DataFrame → OHLCV構造
4. **可視化**: Plotly → インタラクティブローソク足チャート表示
5. **バックテスト表示**: JSON読み込み → 最適化パラメータ・パフォーマンスグラフ表示

### データフロー（レガシー版）

1. **データ収集**: `streamdata.py` → kabusapi → リアルタイムティッカー取得
2. **ローソク足生成**: `candle.py` → SQLiteに時系列データ保存
3. **テクニカル分析**: `dfcandle.py` → 指標計算とバックテスト実行
4. **売買判断**: `ai.py` → 複数指標のシグナル統合
5. **注文執行**: `kabucom.py` → kabusapi経由で発注
6. **可視化**: `webserver.py` → Flask API → `chart.html` → Google Charts

## プロジェクト構成

```
kabucomtrading/
├── .github/                    # GitHub設定
│   ├── dependabot.yml         # 依存関係自動更新設定
│   └── PULL_REQUEST_TEMPLATE.md
├── app/                        # メインアプリケーション
│   ├── controllers/           # コントローラー層
│   │   ├── ai.py             # AIトレーディングロジック
│   │   │                     # - 売買シグナル判定
│   │   │                     # - パラメータ最適化
│   │   │                     # - ストップリミット管理
│   │   ├── streamdata.py     # リアルタイムデータ取得
│   │   │                     # - ティッカーストリーム処理
│   │   │                     # - ローソク足生成トリガー
│   │   └── webserver.py      # Flask Webサーバ
│   │                         # - REST API提供
│   │                         # - テクニカル指標計算エンドポイント
│   ├── data/                 # データ取得層
│   │   ├── __init__.py
│   │   └── yahoo.py          # Yahoo Financeデータ取得
│   │                         # - 過去データ取得
│   │                         # - ティッカー変換
│   │                         # - 時間軸変換
│   ├── models/               # データモデル層
│   │   ├── __init__.py
│   │   ├── base.py          # SQLAlchemy基底クラス
│   │   │                    # - DB接続管理
│   │   │                    # - セッション管理
│   │   ├── candle.py        # ローソク足データモデル
│   │   │                    # - OHLCV構造定義
│   │   │                    # - 時間足別テーブル管理
│   │   ├── dfcandle.py      # DataFrameベースのローソク足
│   │   │                    # - テクニカル指標計算
│   │   │                    # - バックテスト実行
│   │   │                    # - パラメータ最適化
│   │   └── events.py        # シグナルイベント管理
│   │                        # - 売買シグナル記録
│   │                        # - 損益計算
│   └── views/               # ビュー層
│       ├── chart.html       # チャート表示UI (Google Charts)
│       └── google.html      # チャートサンプル
├── kabucom/                  # kabusapi連携
│   └── kabucom.py           # kabusapi クライアント
│                            # - 認証・接続管理
│                            # - 注文・約定処理
│                            # - 残高・ポジション取得
├── tradingalgo/              # アルゴリズム実装
│   └── algo.py              # テクニカル指標計算
│                            # - 一目均衡表
│                            # - カスタム指標
├── utils/                    # ユーティリティ
│   └── utils.py             # 汎用関数
│                            # - 型変換
│                            # - シリアライザ
├── constants.py              # 定数定義
│                            # - 時間足定義
│                            # - 売買区分
│                            # - 銘柄コード
├── settings.py               # 設定読み込み
│                            # - INIファイルパース
│                            # - 環境変数展開
├── main.py                   # エントリーポイント
│                            # - マルチスレッド起動
│                            # - ロギング設定
├── streamlit_app.py          # Streamlitダッシュボード（推奨）
│                            # - インタラクティブUI
│                            # - リアルタイムチャート
│                            # - バックテスト結果表示
├── backtest_yahoo.py         # Yahoo Financeバックテスト
│                            # - 過去データ取得
│                            # - 各指標の最適化
│                            # - 結果レポート生成
├── settings.ini              # 設定ファイル
├── pyproject.toml            # プロジェクト定義・依存関係
├── .pre-commit-config.yaml   # pre-commit設定
├── .python-version           # Python バージョン指定
└── README.md                 # このファイル
```

## 主要コンポーネント詳細

### 1. AI Trading Engine (`app/controllers/ai.py`)

**役割**: 売買判断とパラメータ最適化

**主要クラス**:
- `AI`: トレーディングエンジン本体

**主要メソッド**:
- `update_optimize_params()`: テクニカル指標パラメータの最適化
- `buy()`: 買い注文実行
- `sell()`: 売り注文実行
- `trade()`: 売買シグナル判定と注文実行

**アルゴリズム**:
1. 過去データから複数のテクニカル指標パラメータを最適化
2. 各指標のバックテスト結果から上位N個を選択
3. リアルタイムで複数指標のシグナルを統合
4. シグナル数が閾値を超えたら注文実行
5. ストップリミットで損失を制限

### 2. Data Models (`app/models/`)

#### `candle.py`: ローソク足データ管理
- 時間足別（5秒、1分、1時間）のテーブル定義
- OHLCV（始値、高値、安値、終値、出来高）データ保存
- ティッカーデータからローソク足を自動生成

#### `dfcandle.py`: テクニカル分析
- TA-Libを利用した各種指標計算
- バックテスト機能（過去データでの戦略検証）
- パラメータ最適化（グリッドサーチ）

#### `events.py`: シグナル管理
- 売買シグナルの記録
- 損益計算
- シグナル履歴の取得

### 3. KabusAPI Client (`kabucom/kabucom.py`)

**主要クラス**:
- `KabusApiClient`: APIクライアント
- `Balance`: 残高情報
- `Ticker`: ティッカーデータ
- `Order`: 注文情報
- `Trade`: 約定情報

**主要メソッド**:
- `get_balance()`: 残高取得
- `get_ticker()`: 現在値取得
- `send_order()`: 注文送信
- `get_order()`: 注文状態確認
- `get_open_trade()`: 保有ポジション取得
- `trade_close()`: ポジション決済

### 4. Web API (`app/controllers/webserver.py`)

**エンドポイント**:

#### `GET /`
チャート画面を表示

#### `GET /api/candle/`
ローソク足データとテクニカル指標を取得

**パラメータ**:
- `product_code`: 銘柄コード（必須）
- `duration`: 時間足（5s/1m/1h）
- `limit`: 取得件数（デフォルト: 1000）
- テクニカル指標フラグ（sma, ema, bbands, ichimoku, rsi, macd）
- 各指標のパラメータ（smaPeriod1, bbandsN等）

**レスポンス例**:
```json
{
  "product_code": "1459",
  "duration": "1m",
  "candles": [
    {
      "time": "2025-11-05T10:00:00",
      "open": 1000.0,
      "high": 1005.0,
      "low": 998.0,
      "close": 1003.0,
      "volume": 1000
    }
  ],
  "smas": [
    {
      "period": 7,
      "values": [1000.5, 1001.2, ...]
    }
  ],
  "events": {
    "signals": [],
    "profit": 0.0
  }
}
```

## 技術スタック

### バックエンド
- **Python 3.9+**: メインプログラミング言語
- **Streamlit 1.28+**: インタラクティブWebアプリフレームワーク（推奨）
- **Flask 2.0+**: RESTful APIフレームワーク（レガシー）
- **SQLAlchemy 1.4+**: ORM
- **SQLite**: データベース

### データ分析・可視化
- **NumPy 1.20+**: 数値計算
- **pandas 1.3+**: データ操作・分析
- **Plotly 5.17+**: インタラクティブチャート（Streamlit用）
- **TA-Lib 0.4.17**: テクニカル指標計算
- **yfinance 0.2.0+**: Yahoo Finance データ取得
- **python-dateutil 2.8.0**: 日時処理

### API通信
- **requests 2.25.0+**: HTTP通信

### フロントエンド（レガシー）
- **Lightweight Charts 4.1.3**: TradingView製チャートライブラリ
- **jQuery 3.4.1**: DOM操作

### 開発ツール
- **Ruff**: Linter & Formatter
- **Pyright**: 型チェック
- **Bandit**: セキュリティチェック
- **pre-commit**: Git hooks管理

## データベーススキーマ

### ローソク足テーブル（例: `KABUS_1459_1M`）

| カラム名 | 型 | 説明 |
|---------|-----|------|
| time | DateTime | 時刻（主キー） |
| open | Float | 始値 |
| close | Float | 終値 |
| high | Float | 高値 |
| low | Float | 安値 |
| volume | Integer | 出来高 |

### シグナルイベントテーブル（`signal_event`）

| カラム名 | 型 | 説明 |
|---------|-----|------|
| time | DateTime | 時刻（主キー） |
| product_code | String | 銘柄コード |
| side | String | 売買区分（'1'=売, '2'=買） |
| price | Float | 約定価格 |
| units | Integer | 数量 |

## 使用例

### 1. Streamlitで詳細バックテストを実行

```powershell
# 仮想環境のPythonでStreamlitアプリを起動
 -m streamlit run streamlit_app.py
```

**ブラウザで操作**:
1. http://localhost:8501 にアクセス
2. サイドバーの「🎯 バックテスト」タブを選択
3. 銘柄コード入力（例: `1459`, `7203`, `9984`）
4. ✅ **「詳細モード（全パラメータ結果出力）」にチェック**
5. 「🚀 バックテスト実行」をクリック
6. 結果を確認:
   - パフォーマンス比較グラフ
   - パラメータヒートマップ
   - Top 20ランキング
   - CSVダウンロード

### 2. コマンドラインでバックテスト実行

**標準モード（最適パラメータのみ）**:
```powershell
 backtest_yahoo.py --product-code 1459 --period 90 --duration 1d
```

**詳細モード（全パラメータ組み合わせ）**:
```powershell
 backtest_yahoo.py --detailed --product-code 1459 --period 90 --duration 1d
```

**出力ファイル**:
- `backtest_results.json`: 最適パラメータのサマリー
- `backtest_details/1459_ema_*.csv`: EMA全結果（390パターン）
- `backtest_details/1459_bollinger_bands_*.csv`: BB全結果（40パターン）
- `backtest_details/1459_rsi_*.csv`: RSI全結果（460パターン）
- `backtest_details/1459_macd_*.csv`: MACD全結果（96パターン）

**実行例**:
```
バックテスト結果サマリー
============================================================
銘柄コード: 1459
期間: 90日
時間軸: 1d
------------------------------------------------------------

EMA:
  パフォーマンス: 27.00
  期間1: 23
  期間2: 48
  テスト済み組み合わせ数: 390

Bollinger Bands:
  パフォーマンス: 18.00
  N: 10
  K: 3.00
  テスト済み組み合わせ数: 40

RSI:
  パフォーマンス: 24.00
  期間: 12
  買いスレッド: 25.00
  売りスレッド: 80.00
  テスト済み組み合わせ数: 460

MACD:
  パフォーマンス: 3.00
  Fast期間: 12
  Slow期間: 24
  Signal期間: 11
  テスト済み組み合わせ数: 96
============================================================

詳細結果は backtest_details/ フォルダに保存されました。
```

### 3. 複数銘柄の比較

```powershell
# Streamlitアプリで操作
# 1. サイドバーの「📉 比較」タブを選択
# 2. 比較する銘柄を改行区切りで入力:
#    1459
#    7203
#    9984
# 3. 「📊 比較実行」をクリック
```

### 4. チャートに指標を追加

```powershell
# Streamlitアプリで操作
# 1. サイドバーの「📊 チャート」タブを選択
# 2. テクニカル指標にチェック:
#    ✅ SMA（単純移動平均）→ 期間選択（7, 14, 50など）
#    ✅ EMA（指数移動平均）→ 期間選択（12, 26など）
#    ✅ Bollinger Bands → 期間とK値を調整
#    ✅ 出来高
# 3. 「📊 チャート更新」をクリック
```

## テクニカル指標

以下のテクニカル指標をサポートしています：

- **SMA (単純移動平均)**: 指定期間の平均価格
- **EMA (指数移動平均)**: 直近の価格に重みを置いた移動平均
- **Bollinger Bands**: 価格のボラティリティを表示
- **Ichimoku Cloud (一目均衡表)**: 転換線、基準線、先行スパン、遅行スパン
- **RSI (相対力指数)**: 買われすぎ・売られすぎの判定
- **MACD**: トレンドの強さと方向を判定

## API仕様

### ローソク足データ取得

```
GET /api/candle/?product_code=1459&duration=1m&limit=100
```

#### クエリパラメータ
- `product_code`: 銘柄コード
- `duration`: 時間軸（5s / 1m / 1h）
- `limit`: 取得件数（最大1000）
- `sma`: SMAを含める（true）
- `ema`: EMAを含める（true）
- `bbands`: Bollinger Bandsを含める（true）
- `ichimoku`: Ichimoku Cloudを含める（true）
- `rsi`: RSIを含める（true）
- `macd`: MACDを含める（true）

## 開発

### コード品質ツール

このプロジェクトでは以下のツールを使用しています：

- **Ruff**: Linter & Formatter
- **Pyright**: 型チェック
- **Bandit**: セキュリティチェック
- **pre-commit**: コミット前チェック

### コード整形

```bash
ruff format .
```

### Lint実行

```bash
ruff check .
```

### 型チェック

```bash
pyright
```

## トラブルシューティング

### TA-Libのインストールエラー

TA-Libはネイティブライブラリのため、事前にシステムレベルでのインストールが必要です。
公式サイトまたはパッケージマネージャーを利用してインストールしてください。

### kabusapi接続エラー

- `settings.ini`のトークンとURLが正しいか確認してください
- kabu.com証券のAPIサービスが起動しているか確認してください
- 証明書エラーが発生する場合は、`verify=False`が設定されているか確認してください（本番環境では非推奨）

## ライセンス

MIT License

## 免責事項

本ソフトウェアは教育・研究目的で提供されています。
実際の取引での使用により生じたいかなる損失についても、作者は一切の責任を負いません。
金融商品取引にはリスクが伴います。自己責任でご利用ください。

## 参考リンク

- [kabu.com証券API公式ドキュメント](https://kabucom.github.io/kabusapi/)
- [kabusapi GitHub](https://github.com/kabucom/kabusapi)
- [TA-Lib](https://www.ta-lib.org/)
