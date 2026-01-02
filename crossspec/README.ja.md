# CrossSpec（日本語）

CrossSpec は、一般的な業務ドキュメントから「クレーム（Claim）」を抽出し、JSONL 形式で出力する CLI ファーストのツールです。抽出したテキストは `text_raw` として改変せず保持し、由来情報（provenance）と正規化ハッシュ（SHA-256）を付与します。必要に応じて、ユーザー定義のタクソノミーに基づく LLM タグ付けも可能です。

## 特長

- PDF / XLSX / PPTX / EML からの抽出に対応
- 原文保持（`text_raw`）と由来情報の付与
- 正規化ハッシュによる改ざん検知
- タクソノミー制約下の任意タグ付け（LLM）
- 形式ごとに拡張しやすいモジュール構造

## クイックスタート

```bash
uv venv
source .venv/bin/activate
uv pip install -e ./crossspec

cp crossspec/crossspec.yml.example crossspec.yml
crossspec extract --config crossspec.yml
```

## デモ（効果確認）

```bash
uv pip install -e ./crossspec\[demo\]

crossspec demo --config samples/crossspec.yml
```

PDF を含むサンプルデータを生成し、抽出結果のサマリを出力します。

※ `facets.feature` は複数ラベルのため、合計件数は全クレーム数を超える場合があります。

### 出力例

```
Generated 3 EML files in /path/to/SpecDiff/samples/input/mail
Generated /path/to/SpecDiff/samples/input/sample.xlsx
Generated /path/to/SpecDiff/samples/input/sample.pptx
Generated /path/to/SpecDiff/samples/input/sample.pdf
Wrote 18 claims to samples/output/claims.jsonl
Counts by source.type:
  pdf: 2
  xlsx: 10
  pptx: 3
  eml: 3
Counts by authority:
  normative: 2
  approved_interpretation: 9
  informative: 7
Counts by facets.feature:
  brake: 6
  can: 4
  error_handling: 7
  timing: 5
  diagnostics: 5
  safety: 7
  calibration: 5
  nvm: 4
  init: 2
  comms: 1
Note: Counts by facets.feature is multi-label; totals can exceed total claims.
Sample claims:
TYPE: eml | CLM-BRAKE-000005 | samples/input/mail/mail1.eml | {...}
  From: demo1@example.com To: team@example.com Date: Fri, 01 Mar 2024 10:00:00 +0000 ...
TYPE: pdf | CLM-BRAKE-000001 | samples/input/sample.pdf | {...}
  Brake controller shall support safe deceleration under normal conditions ...
TYPE: pptx | CLM-BRAKE-000004 | samples/input/sample.pptx | {...}
  [Slide 1] Brake Feature Overview ...
TYPE: xlsx | CLM-BRAKE-000002 | samples/input/sample.xlsx | {...}
  Question: How is brake torque limited? Answer: Via controller thresholds. ...
```

## 検索

```bash
crossspec search --config samples/crossspec.yml --feature brake --top 5
crossspec search --config samples/crossspec.yml --query "timing" --type pdf
```

## セットアップ用スクリプト（任意）

```bash
./scripts/setup_demo.sh
```

## ワンコマンド実行スクリプト

```bash
./scripts/run_demo.sh
```

`run_demo.sh` は、サンプル生成と抽出に加えて、`outputs/code_claims.jsonl` へコード抽出も実行します。`code-extract` は既定で `outputs/` や `samples/output/` などの生成物ディレクトリを除外するため、生成済みの JSONL を再スキャンしません。

## コード抽出（code-extract）

```bash
crossspec code-extract --repo . --out outputs/code_claims.jsonl --unit function --language python
```

- 既定の除外パターンにより、`outputs/`、`samples/output/`、`samples/input/`、`.ruff_cache/`、`.tox/` などの生成物はスキャン対象外です。
- `--out` で指定した JSONL も自動的に除外されます。

## Ollama によるタグ付け（任意）

Ollama の OpenAI 互換 API を使ってローカルでタグ付けできます。

```bash
ollama pull gpt-oss:20b
```

`crossspec.yml` の例:

```yaml
tagging:
  enabled: true
  provider: "llm"
  taxonomy_path: "taxonomy/features.yaml"
  llm:
    model: "gpt-oss:20b"
    base_url: "http://localhost:11434/v1"
    api_key: "ollama"
    temperature: 0.0
  output:
    facets_key: "facets"
```

タグ付けは任意で、`tagging.enabled` を `false` にすると無効化できます。

## サンプル設定

`crossspec.yml.example` を参照してください。

## Claim スキーマ（概要）

**必須**
- `schema_version`, `claim_id`, `authority`, `status`
- `text_raw`, `hash`, `source`, `provenance`
- `created_at`, `extracted_by`

**任意**
- `text_norm`, `facets`, `relations`

## 対応フォーマット

- **PDF**: テキストブロックから段落単位で抽出
- **XLSX**: 行単位で指定列を結合
- **PPTX**: スライド単位、必要に応じてノートも取得
- **EML**: メールヘッダと本文を抽出

## 開発

```bash
pytest
```
