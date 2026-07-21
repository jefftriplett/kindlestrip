"""Helpers for building synthetic Mobipocket files for the test suite.

These build the minimal amount of a PDB/Mobipocket structure that
``SRCSStripper`` actually inspects: the ``BOOKMOBI`` type/creator at 0x3C,
the record count at offset 76, the 8-byte-per-record offset table starting
at offset 78, and a record 0 (mobiheader) whose SRCS pointer lives at 0xE0.
"""

from __future__ import annotations

import struct

# A record 0 (mobiheader) must be at least 0xE8 bytes so the SRCS pointer at
# 0xE0 fits inside it.
MOBIHEADER_LEN = 240


def make_mobiheader(srcs_secnum: int, srcs_cnt: int) -> bytes:
    """Build a record-0 mobiheader with the SRCS pointer set at offset 0xE0."""
    header = bytearray(b"\x00" * MOBIHEADER_LEN)
    header[0:8] = b"MOBI\x00\x00\x00\xe4"
    struct.pack_into(">2L", header, 0xE0, srcs_secnum, srcs_cnt)
    return bytes(header)


def make_srcs_record(
    kind: bytes = b"SRCS", payload: bytes = b"source-archive"
) -> bytes:
    """Build a SRCS/CMET record: a 16-byte header followed by the payload."""
    header = kind + b"\x00" * (16 - len(kind))
    return header + payload


def build_mobi(sections: list[bytes], srcs_secnum: int, srcs_cnt: int) -> bytes:
    """Assemble a minimal ``BOOKMOBI`` PDB file from ``sections``.

    ``sections[0]`` is the mobiheader; ``srcs_secnum``/``srcs_cnt`` are written
    into it via :func:`make_mobiheader` by the caller.
    """
    num_sections = len(sections)

    header = bytearray(78)
    header[0x3C : 0x3C + 8] = b"BOOKMOBI"
    struct.pack_into(">H", header, 76, num_sections)

    # 2 bytes of null padding conventionally sit between the record table and
    # the first record's data.
    data_start = 78 + (8 * num_sections) + 2

    offsets = []
    off = data_start
    for section in sections:
        offsets.append(off)
        off += len(section)

    table = bytearray()
    for i, offset in enumerate(offsets):
        # flags/uid byte pattern is preserved verbatim by the stripper; the
        # exact value is irrelevant, so use the record index.
        table += struct.pack(">L", offset) + struct.pack(">L", i)

    return bytes(header) + bytes(table) + b"\x00\x00" + b"".join(sections)


def default_sections(
    srcs_cnt: int = 1,
    before: bytes = b"BEFORE-CONTENT-RECORD",
    after: bytes = b"AFTER-CONTENT-RECORD",
) -> tuple[list[bytes], int]:
    """Return ``(sections, srcs_secnum)`` for a standard test file.

    Layout: ``[mobiheader, before, SRCS(, CMET...), after]``.
    """
    srcs_secnum = 2
    srcs_records = [make_srcs_record(b"SRCS", b"source-archive-zip-bytes")]
    if srcs_cnt >= 2:
        srcs_records.append(make_srcs_record(b"CMET", b"build-log-text"))
    for i in range(2, srcs_cnt):
        srcs_records.append(make_srcs_record(b"SRCS", b"extra-%d" % i))

    sections = [
        make_mobiheader(srcs_secnum, srcs_cnt),
        before,
        *srcs_records,
        after,
    ]
    return sections, srcs_secnum


def make_default_mobi(srcs_cnt: int = 1) -> bytes:
    """Return a ready-to-strip synthetic Mobipocket file."""
    sections, srcs_secnum = default_sections(srcs_cnt=srcs_cnt)
    return build_mobi(sections, srcs_secnum, srcs_cnt)
