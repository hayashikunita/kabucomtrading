# kabucomtrading

kabu.com証券のAPI（kabusapi）を利用した株式・ETF自動売買システムです。  
テクニカル指標によるシグナル生成、バックテスト機能、リアルタイムデータ可視化を提供します。

## ⚠️ 注意事項

**本プロジェクトは現在開発中です。**  
仕様や構成は予告なく変更される可能性があります。  
実際の取引での使用は自己責任でお願いします。

## 機能

- **自動売買**: kabusapi経由での注文執行
- **テクニカル指標**: SMA, EMA, Bollinger Bands, Ichimoku Cloud, RSI, MACD
- **バックテスト**: 過去データを用いた戦略検証
- **パラメータ最適化**: 複数のテクニカル指標パラメータを自動最適化
- **リアルタイムデータ取得**: ストリーミングティッカーデータの収集
- **Webダッシュボード**: ローソク足チャートとテクニカル指標の可視化
- **データ永続化**: SQLiteによる時系列データ・シグナル管理

## 必要要件

- Python 3.9以上（推奨: 3.12）
- kabu.com証券のAPIトークン
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
pip install -e .
```

または

```bash
pip install dict2obj Flask numpy python-dateutil requests SQLAlchemy TA-Lib
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

## 使い方

### 基本的な起動

```bash
python main.py
```

これにより以下が起動します：
- ストリーミングデータ取得スレッド
- Webサーバ（デフォルト: http://localhost:8080）

### Webダッシュボードへのアクセス

ブラウザで `http://localhost:8080` にアクセスすると、チャートとテクニカル指標を確認できます。

#### データソースの切り替え

Webダッシュボードでは、以下の2つのデータソースを切り替えて表示できます：

1. **Yahoo Finance**: Yahoo Financeから過去データを取得して表示（デフォルト）
   - kabusapi接続不要
   - 過去データの分析に最適
   - 1分足は最大7日分、日足は長期間取得可能

2. **kabusapi**: kabu.com証券のAPIからリアルタイムデータを取得
   - APIトークンと接続が必要
   - リアルタイムトレーディングに使用

画面上部の「データソース」ボタンで切り替えが可能です。また、時間軸（5秒足/1分足/1時間足）も選択できます。

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

```bash
python backtest_yahoo.py
```うv

このスクリプトは以下を実行します：
1. Yahoo Financeから `settings.ini` で指定した銘柄の過去データを取得
2. 複数のテクニカル指標（EMA, Bollinger Bands, Ichimoku, RSI, MACD）でバックテスト
3. 各指標の最適パラメータを探索
4. 結果をコンソールに表示し、`backtest_results.json` に保存

#### 3. 出力例

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

Bollinger Bands:
  パフォーマンス: 980.30
  N: 20
  K: 2.00

Ichimoku Cloud:
  パフォーマンス: 1100.75

RSI:
  パフォーマンス: 850.20
  期間: 14
  買いスレッド: 30.00
  売りスレッド: 70.00

MACD:
  パフォーマンス: 1050.40
  Fast期間: 12
  Slow期間: 26
  Signal期間: 9
============================================================
```

#### 4. Yahoo Financeデータの制限事項

- **1分足**: 最大7日間のデータのみ取得可能
- **5分足**: 最大60日間のデータのみ取得可能
- **1時間足/日足**: 長期間のデータ取得可能
- **5秒足**: Yahoo Financeは対応していないため、1分足で代用

#### 5. カスタマイズ

`backtest_yahoo.py` を編集して、以下をカスタマイズできます：
- 銘柄コード（デフォルト: `settings.product_code`）
- 期間（デフォルト: `settings.past_period` 日）
- 時間軸（デフォルト: `settings.trade_duration`）
- 市場コード（デフォルト: 'T' = 東証）

例：
```python
# 特定の銘柄で実行
backtest = YahooBacktest('7203', 365, '1d')  # トヨタ自動車、365日、日足
backtest.run_backtest()
```

## アーキテクチャ

このプロジェクトは、以下のレイヤーで構成されています：

### システム構成図

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

### データフロー

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
- **Python 3.6+**: メインプログラミング言語
- **Flask 1.0.2**: Webフレームワーク
- **SQLAlchemy 1.3.7**: ORM
- **SQLite**: データベース

### データ分析
- **NumPy 1.16.0**: 数値計算
- **TA-Lib 0.4.17**: テクニカル指標計算
- **python-dateutil 2.8.0**: 日時処理
- **yfinance 0.2.0+**: Yahoo Finance データ取得

### API通信
- **requests 2.23.0**: HTTP通信

### フロントエンド
- **Google Charts**: チャート可視化
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