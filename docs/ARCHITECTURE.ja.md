# CrossSpec アーキテクチャ（日本語）

## 目的
CrossSpec は、業務ドキュメントから不変のクレーム（Claim）を抽出し、JSONL として出力します。原文保持・由来情報・ハッシュにより、監査性と追跡性を確保します。

## 非目標（MVP）
- ベクターデータベースへのインデックスは実装しない（将来の拡張）。
- UI は提供しない（CLI のみ）。
- Claim ID の永続的な安定性は保証しない（実行ごとにリセット）。
- 高度な本文整形や返信除去は行わない。

## データフロー
1. **入力**: `crossspec.yml` で指定されたファイルパターン
2. **抽出器**: 形式別の Extractor が `ExtractedClaim` を生成
3. **Claim 組み立て**: ID 生成、正規化、ハッシュ付与
4. **JSONL 出力**: 1 行 1 Claim
5. **任意タグ付け**: タクソノミーに従って facets を付与

## 主要モジュール
- `src/crossspec/cli.py`: CLI エントリポイント（`extract`, `index`, `analyze`, `demo`）
- `src/crossspec/config.py`: YAML 設定の読み込み
- `src/crossspec/claims.py`: Claim スキーマと ID 生成
- `src/crossspec/normalize.py`: `normalize_light`
- `src/crossspec/hashing.py`: SHA-256 ハッシュ
- `src/crossspec/io/jsonl.py`: JSONL 出力
- `src/crossspec/extract/*_extractor.py`: 形式別抽出
- `src/crossspec/tagging/*`: タクソノミーと LLM タグ付け

## Claim スキーマ
**必須**
- `schema_version`, `claim_id`, `authority`, `status`
- `text_raw`, `hash`, `source`, `provenance`
- `created_at`, `extracted_by`

**任意**
- `text_norm`, `facets`, `relations`

## 新しい抽出器の追加方法
1. `src/crossspec/extract/` に Extractor を実装。
2. `ExtractedClaim` を返すように実装。
3. `cli._build_extractor` に分岐を追加。
4. 必要であれば config スキーマを拡張。

## 既知の制約
- オプション依存（PyMuPDF, openpyxl, python-pptx 等）が未導入の場合は該当形式で失敗。
- PDF の抽出品質は原文構造に依存。
- Claim ID は実行ごとにリセット。

## スモークテスト
```bash
make smoke
```

## デモ
```bash
crossspec demo --config samples/crossspec.yml
```

サンプルデータを生成し、抽出結果のサマリを出力します。
