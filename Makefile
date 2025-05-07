.PHONY: test example clean install dev

# 開発用インストール
dev:
	pip install -e ".[dev]"

# 通常インストール
install:
	pip install -e .

# テスト実行
test:
	pytest

# 例の実行
example:
	python examples/simple.py

# クリーンアップ
clean:
	rm -rf build/ dist/ *.egg-info/ __pycache__/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete 