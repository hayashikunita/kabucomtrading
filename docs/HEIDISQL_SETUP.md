# HeidiSQLからデータ投入する手順

このプロジェクトの既定DBは SQLite です。

- DBファイル: `stockdata.sql`
- 基本テーブル命名: `CANDLE_<銘柄コード>_<時間軸>`
  - 例: 7203 + 1d => `CANDLE_7203_1D`

## 1. 先にテーブルを作る

PowerShellで以下を実行します。

```bash
uv run python prepare_candle_table.py --code 7203 --duration 1d
```

成功すると `prepared_table=...` が表示されます。

## 2. HeidiSQLでSQLiteへ接続

1. 新規セッション作成
2. ネットワーク種別で SQLite を選択（バージョンにより表記差あり）
3. DBファイルに `stockdata.sql` を指定
4. 接続

## 3. 手入力で1行追加する

対象テーブル (`CANDLE_7203_1D` など) を開き、以下カラムに入力します。

- `time` (YYYY-MM-DD HH:MM:SS)
- `open`
- `close`
- `high`
- `low`
- `volume`

`time` は主キーです。同一時刻は重複登録できません。

## 4. CSVから投入する

1. HeidiSQLで対象テーブルを右クリック
2. Import CSV file を選択
3. 列対応を次のように合わせる
   - time, open, close, high, low, volume
4. 実行

CSVテンプレートはこれを使えます:

- `templates/heidisql_candle_template.csv`

## 5. アプリ側で確認

- Streamlit起動後、該当銘柄・時間軸でチャート更新
- またはAPIで確認: `/api/candle/?product_code=7203&duration=1d&limit=100`

## うまくいかない場合

- SQLite接続項目が無い場合: HeidiSQLのバージョン差異です。最新版更新を試してください。
- テーブルが見えない場合: 先に `prepare_candle_table.py` を実行してください。
- 文字列日時で失敗する場合: `YYYY-MM-DD HH:MM:SS` 形式で投入してください。
