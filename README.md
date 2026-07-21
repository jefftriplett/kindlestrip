# kindlestrip

A pip install-able conversion of Paul Durrant's kindlestrip library to strip the penultimate record from a Mobipocket file. (http://www.mobileread.com/forums/showthread.php?t=96903)

## Usage

To install:

```shell
pip install kindlestrip
```

To use:

```shell
$ kindlestrip input.mobi output.mobi

$ du -sh *
268K    input.mobi
200K    output.mobi
```

Or run it without installing, straight from PyPI with
[uv](https://docs.astral.sh/uv/):

```shell
$ uvx kindlestrip input.mobi output.mobi
```

`kindlestrip.py` is also a self-contained [PEP 723](https://peps.python.org/pep-0723/)
script, so you can run the local file without installing anything:

```shell
$ uv run kindlestrip.py input.mobi output.mobi
```

Options:

```shell
$ kindlestrip --help
$ kindlestrip -d input.mobi output.mobi   # also dump the stripped SRCS records
```

## Development

Requires Python 3.10–3.14. Common tasks are in the `justfile`:

```shell
$ just test    # run pytest
$ just lint     # ruff check + format
$ just build    # build sdist + wheel
```
