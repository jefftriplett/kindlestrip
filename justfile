@_default:
    just --list

@test:
    pytest

@build:
    python -m build

@check:
    twine check dist/*

@upload:
    twine upload dist/*
