@_default:
    just --list

@test:
    pytest

@build:
    python -m build

@check:
    twine check dist/*

@pre-commit:
    git ls-files -- . | xargs pre-commit run --config=.pre-commit-config.yaml --files

@upload:
    twine upload dist/*
