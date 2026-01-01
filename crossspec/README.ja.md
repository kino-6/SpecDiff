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

## セットアップ用スクリプト（任意）

```bash
./scripts/setup_demo.sh
```

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
