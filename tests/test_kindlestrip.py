from __future__ import annotations

import struct
from pathlib import Path

import pytest
from conftest import build_mobi
from conftest import default_sections
from conftest import make_default_mobi
from conftest import make_mobiheader

import kindlestrip
from kindlestrip import SRCSStripper
from kindlestrip import StripException


def read_srcs_pointer(data: bytes) -> tuple[int, int]:
    """Read ``(srcs_secnum, srcs_cnt)`` from a file's record-0 mobiheader."""
    offset0, _ = struct.unpack_from(">2L", data, 78)
    offset1, _ = struct.unpack_from(">2L", data, 86)
    mobiheader = data[offset0:offset1]
    return struct.unpack_from(">2L", mobiheader, 0xE0)


def test_strip_shrinks_file_by_srcs_length():
    data = make_default_mobi()
    stripper = SRCSStripper(data)
    result = stripper.get_result()
    assert len(result) == len(data) - stripper.srcs_length


def test_strip_removes_srcs_payload():
    data = make_default_mobi()
    assert b"source-archive-zip-bytes" in data
    result = SRCSStripper(data).get_result()
    assert b"source-archive-zip-bytes" not in result


def test_strip_nulls_mobiheader_srcs_pointer():
    data = make_default_mobi()
    result = SRCSStripper(data).get_result()
    srcs_secnum, srcs_cnt = read_srcs_pointer(result)
    assert srcs_secnum == 0xFFFFFFFF
    assert srcs_cnt == 0


def test_strip_preserves_surrounding_records():
    data = make_default_mobi()
    result = SRCSStripper(data).get_result()
    assert b"BEFORE-CONTENT-RECORD" in result
    assert b"AFTER-CONTENT-RECORD" in result


def test_restripping_reports_no_sources_section():
    data = make_default_mobi()
    result = SRCSStripper(data).get_result()
    with pytest.raises(StripException, match="doesn't contain the sources"):
        SRCSStripper(result)


def test_invalid_file_format_raises():
    with pytest.raises(StripException, match="invalid file format"):
        SRCSStripper(b"this is definitely not a mobipocket file" * 4)


def test_missing_srcs_section_raises():
    sections, srcs_secnum = default_sections()
    sections[0] = make_mobiheader(0xFFFFFFFF, 0)
    data = build_mobi(sections, srcs_secnum, srcs_cnt=1)
    with pytest.raises(StripException, match="doesn't contain the sources"):
        SRCSStripper(data)


def test_get_stripped_data_and_header():
    data = make_default_mobi()
    stripper = SRCSStripper(data)
    headers = stripper.get_header()
    payloads = stripper.get_stripped_data()
    assert len(headers) == 1
    assert headers[0][0:4] == b"SRCS"
    assert payloads[0] == b"source-archive-zip-bytes"


def test_multiple_srcs_sections_are_all_stripped():
    data = make_default_mobi(srcs_cnt=2)
    stripper = SRCSStripper(data)
    result = stripper.get_result()
    assert stripper.srcs_cnt == 2
    assert [h[0:4] for h in stripper.get_header()] == [b"SRCS", b"CMET"]
    assert b"source-archive-zip-bytes" not in result
    assert b"build-log-text" not in result
    assert read_srcs_pointer(result) == (0xFFFFFFFF, 0)


def test_main_strips_file(tmp_path: Path):
    infile = tmp_path / "in.mobi"
    outfile = tmp_path / "out.mobi"
    data = make_default_mobi()
    infile.write_bytes(data)

    rc = kindlestrip.main([str(infile), str(outfile)])

    assert rc == 0
    result = outfile.read_bytes()
    assert len(result) < len(data)
    assert read_srcs_pointer(result) == (0xFFFFFFFF, 0)


def test_main_returns_1_on_invalid_input(tmp_path: Path):
    infile = tmp_path / "bad.mobi"
    outfile = tmp_path / "out.mobi"
    infile.write_bytes(b"not a mobi at all" * 8)

    rc = kindlestrip.main([str(infile), str(outfile)])

    assert rc == 1
    assert not outfile.exists()


def test_main_dump_writes_stripped_records(tmp_path: Path, monkeypatch):
    infile = tmp_path / "in.mobi"
    outfile = tmp_path / "out.mobi"
    infile.write_bytes(make_default_mobi(srcs_cnt=2))
    monkeypatch.chdir(tmp_path)

    rc = kindlestrip.main(["-d", str(infile), str(outfile)])

    assert rc == 0
    assert (
        tmp_path / "kindlestrip_source_archive.zip"
    ).read_bytes() == b"source-archive-zip-bytes"
    assert (tmp_path / "kindlestrip_build_log.txt").read_bytes() == b"build-log-text"


def test_main_version_flag_exits_zero(capsys):
    with pytest.raises(SystemExit) as excinfo:
        kindlestrip.main(["--version"])
    assert excinfo.value.code == 0
    assert kindlestrip.__version__ in capsys.readouterr().out


def test_main_requires_two_positional_args():
    with pytest.raises(SystemExit) as excinfo:
        kindlestrip.main(["only-one-arg"])
    assert excinfo.value.code == 2


SAMPLE_INPUT = Path(__file__).resolve().parent.parent.parent / "input.mobi"


@pytest.mark.skipif(not SAMPLE_INPUT.exists(), reason="sample input.mobi not available")
def test_real_sample_mobi_strips_and_shrinks(tmp_path: Path):
    data = SAMPLE_INPUT.read_bytes()
    stripper = SRCSStripper(data)
    result = stripper.get_result()
    assert len(result) < len(data)
    assert read_srcs_pointer(result) == (0xFFFFFFFF, 0)
