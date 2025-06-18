# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

pydantic-autocliは、PydanticモデルからCLIアプリケーションを自動生成するPythonライブラリです。Pydanticモデルのフィールドをコマンドライン引数に変換し、サブコマンド、型検証、非同期処理をサポートします。

## 開発コマンド

### パッケージ管理
- `uv sync` - 開発依存関係を含むすべての依存関係をインストール
- `uv add <package>` - 新しい依存関係を追加
- `uv add --dev <package>` - 開発依存関係を追加

### テスト
- `uv run pytest` - すべてのテストを実行
- `uv run task coverage` - カバレッジレポート付きでテストを実行
- `pytest --cov=pydantic_autocli --cov-report=term-missing --disable-warnings` - 完全なカバレッジコマンド

### サンプル実行
- `uv run task example` - 基本サンプル（examples/example.py）を実行
- `python examples/example.py greet --verbose` - 特定のコマンドでサンプルを実行
- `uv run task example file --file README.md` - fileコマンドでサンプルを実行

### ユーティリティ
- `uv run task clean` - ビルド成果物とキャッシュファイルをクリーンアップ

## アーキテクチャ

### コアコンポーネント

1. **AutoCLIクラス** (`pydantic_autocli/cli.py:156`)
   - CLIアプリケーションのメインベースクラス
   - `run_*`メソッドを自動発見し、CLIコマンドに変換
   - 引数解析、型検証、コマンド実行を処理
   - 同期・非同期両方のコマンドメソッドをサポート

2. **引数解決システム** (`pydantic_autocli/cli.py:357`)
   - 3段階の優先順位で引数クラスを解決：
     1. メソッドパラメータの型アノテーション
     2. 命名規則（例：`run_command`に対する`CommandArgs`）
     3. `CommonArgs`へのフォールバック
   - 型アノテーションと命名規則の競合を処理

3. **フィールド登録** (`pydantic_autocli/cli.py:68`)
   - Pydanticモデルフィールドをargparse引数に変換
   - `param()`ヘルパーまたは`json_schema_extra`付き`Field()`によるカスタムCLIオプションをサポート
   - プリミティブ型、真偽値、配列、選択制約を処理

### 主要パターン

- **コマンドメソッド**: `run_`で始まるメソッドがCLIサブコマンドになる
  - `run_command` → `command`サブコマンド
  - `run_foo_bar` → `foo-bar`サブコマンド（snake_caseからkebab-caseに変換）

- **引数クラス**: CLI引数を定義するPydanticモデル
  - `BaseModel`または`AutoCLI.CommonArgs`から継承する必要がある
  - 短縮形や選択肢などのCLI固有オプションには`param()`ヘルパーを使用
  - 自動argparse設定のための型アノテーションをサポート

- **リターンコード**: コマンドメソッドが返す値：
  - `None`または`True` → 終了コード0
  - `False` → 終了コード1
  - `int` → カスタム終了コード

### プロジェクト構造

- `pydantic_autocli/` - メインパッケージディレクトリ
  - `__init__.py` - パブリックAPIエクスポート
  - `cli.py` - コアAutoCLI実装
- `examples/` - 使用例
- `tests/` - 引数解析、クラス解決、戻り値の型をカバーするテストスイート
- hatchlingビルドシステムとuvによる依存関係管理でpyproject.tomlを使用

## テストに関する注記

テストスイートは3つの主要領域をカバーしています：
- `test_arg_parsing.py` - CLI引数解析と検証
- `test_class_resolution.py` - 引数クラス解決ロジック
- `test_return_types.py` - コマンド戻り値の処理

すべてのテストはpytestを使用し、適切な依存関係分離を確保するため`uv run pytest`で実行する必要があります。