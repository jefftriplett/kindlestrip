@_default:
    just --list

@build:
    python -m build

@bump:
    bumpversion minor

@check:
    twine check dist/*

@pre-commit:
    git ls-files -- . | xargs pre-commit run --config=.pre-commit-config.yaml --files

@test:
    pytest

@upload:
    twine upload dist/*
