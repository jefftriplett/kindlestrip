@_default:
    just --list

@build:
    python -m build

@bump:
    bump-my-version bump minor

@check:
    twine check dist/*

@lint:
    uvx ruff check .
    uvx ruff format --check .

@pre-commit:
    git ls-files -- . | xargs pre-commit run --config=.pre-commit-config.yaml --files

@test:
    pytest

@upload:
    twine upload dist/*
