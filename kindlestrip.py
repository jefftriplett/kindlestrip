#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
#
# This script strips the penultimate record from a Mobipocket file.
# This is useful because the current KindleGen adds a compressed copy
# of the source files used in this record, making the ebook produced
# about twice as big as it needs to be.
#
# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# For more information, please refer to <http://unlicense.org/>
#
# Written by Paul Durrant, 2010-2011, paul@durrant.co.uk
#
# Changelog
#  1.00 - Initial version
#  1.10 - Added an option to output the stripped data
#  1.20 - Added check for source files section (thanks Piquan)
#  1.30 - Added Support for K8 style mobis
#  1.31 - To get K8 style mobis to work properly, need to replace SRCS section with section of 0 length
#  1.35a- Backport of fixes from 1.32-1.35 to 1.31 to workaround latest Kindlegen changes
#  1.36 - Backport of updates
#  1.37 - Python3 support
#  1.38 - Python3 fixes
#  1.39 - Modernized for Python 3.10+: argparse, pathlib, type hints, PEP 723
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

__version__ = "2026.7.0"

__all__ = ["SRCSStripper", "StripException", "main"]


class StripException(Exception):
    """Raised when a Mobipocket file cannot be stripped."""


def patchdata(datain: bytes, off: int, new: bytes) -> bytes:
    """Return ``datain`` with ``new`` overwriting the bytes starting at ``off``."""
    return b"".join([datain[:off], new, datain[off + len(new) :]])


def joindata(datain: bytes, new: bytes) -> bytes:
    """Return ``datain`` with ``new`` appended."""
    return b"".join([datain, new])


class SRCSStripper:
    """Strip the SRCS (sources) records from a Mobipocket file's bytes.

    The whole transformation happens in ``__init__``; the rebuilt file is
    available via :meth:`get_result`, and the removed records via
    :meth:`get_stripped_data` / :meth:`get_header`.
    """

    def sec_info(self, secnum: int) -> tuple[int, int, int]:
        """Return ``(start_offset, flags, next_offset)`` for PDB record ``secnum``."""
        start_offset, flgval = struct.unpack_from(
            ">2L",
            self.datain,
            78 + (secnum * 8),
        )
        if secnum == self.num_sections:
            next_offset = len(self.datain)
        else:
            next_offset, _nflgval = struct.unpack_from(
                ">2L",
                self.datain,
                78 + ((secnum + 1) * 8),
            )
        return start_offset, flgval, next_offset

    def load_section(self, secnum: int) -> bytes:
        """Return the raw bytes of PDB record ``secnum``."""
        start_offset, _tval, next_offset = self.sec_info(secnum)
        return self.datain[start_offset:next_offset]

    def __init__(self, datain: bytes) -> None:
        if datain[0x3C : 0x3C + 8] != b"BOOKMOBI":
            raise StripException("invalid file format")
        self.datain = datain
        (self.num_sections,) = struct.unpack(">H", datain[76:78])

        # get mobiheader
        mobiheader = self.load_section(0)

        # get SRCS section number and count
        self.srcs_secnum, self.srcs_cnt = struct.unpack_from(">2L", mobiheader, 0xE0)
        if self.srcs_secnum == 0xFFFFFFFF or self.srcs_cnt == 0:
            raise StripException("File doesn't contain the sources section.")

        print("SRCS section number is:", self.srcs_secnum)
        print("SRCS section count is:", self.srcs_cnt)

        # store away srcs sections in case the user wants them later
        self.srcs_headers: list[bytes] = []
        self.srcs_data: list[bytes] = []
        for i in range(self.srcs_secnum, self.srcs_secnum + self.srcs_cnt):
            data = self.load_section(i)
            self.srcs_headers.append(data[0:16])
            self.srcs_data.append(data[16:])

        # find its SRCS region starting offset and total length
        self.srcs_offset, _fval, _temp2 = self.sec_info(self.srcs_secnum)
        after_srcs = self.srcs_secnum + self.srcs_cnt
        next_offset, _temp1, _temp2 = self.sec_info(after_srcs)
        self.srcs_length = next_offset - self.srcs_offset
        print("SRCS length is: 0x%x" % self.srcs_length)

        if self.datain[self.srcs_offset : self.srcs_offset + 4] != b"SRCS":
            raise StripException("SRCS section num does not point to SRCS.")

        # first write out the number of sections
        self.data_file = self.datain[:76]
        self.data_file = joindata(
            self.data_file,
            struct.pack(">H", self.num_sections),
        )

        # we are going to make the SRCS section lengths all be 0.
        # offsets up to and including the first srcs record must not be changed.
        last_offset = -1
        for i in range(self.srcs_secnum + 1):
            offset, flgval, _temp = self.sec_info(i)
            last_offset = offset
            self.data_file = joindata(
                self.data_file,
                struct.pack(">L", offset) + struct.pack(">L", flgval),
            )

        # for every additional record in SRCS records set start to last_offset
        # (they are all zero length)
        for i in range(self.srcs_secnum + 1, self.srcs_secnum + self.srcs_cnt):
            _temp1, flgval, _temp2 = self.sec_info(i)
            self.data_file = joindata(
                self.data_file,
                struct.pack(">L", last_offset) + struct.pack(">L", flgval),
            )

        # for every record after the SRCS records we must start it earlier by an
        # amount equal to the total length of all of the SRCS sections
        delta = 0 - self.srcs_length
        for i in range(self.srcs_secnum + self.srcs_cnt, self.num_sections):
            offset, flgval, _temp = self.sec_info(i)
            offset += delta
            self.data_file = joindata(
                self.data_file,
                struct.pack(">L", offset) + struct.pack(">L", flgval),
            )

        # now pad it out to begin right at the first offset
        # typically this is 2 bytes of nulls
        first_offset, _flgval = struct.unpack_from(">2L", self.data_file, 78)
        self.data_file = joindata(
            self.data_file,
            b"\0" * (first_offset - len(self.data_file)),
        )

        # now add on everything up to the original srcs_offset and then
        # everything after it
        self.data_file = b"".join(
            [
                self.data_file,
                self.datain[first_offset : self.srcs_offset],
                self.datain[self.srcs_offset + self.srcs_length :],
            ],
        )

        # update the srcs_secnum and srcs_cnt in the new mobiheader
        offset0, _flgval0 = struct.unpack_from(">2L", self.data_file, 78)
        offset1, _flgval1 = struct.unpack_from(">2L", self.data_file, 86)
        mobiheader = self.data_file[offset0:offset1]
        mobiheader = (
            mobiheader[:0xE0]
            + struct.pack(">L", 0xFFFFFFFF)
            + struct.pack(">L", 0)
            + mobiheader[0xE8:]
        )
        self.data_file = patchdata(self.data_file, offset0, mobiheader)
        print("done")

    def get_result(self) -> bytes:
        """Return the rebuilt Mobipocket file with the SRCS records stripped."""
        return self.data_file

    def get_stripped_data(self) -> list[bytes]:
        """Return the payloads of the stripped SRCS records."""
        return self.srcs_data

    def get_header(self) -> list[bytes]:
        """Return the 16-byte headers of the stripped SRCS records."""
        return self.srcs_headers


def _dump_stripped_records(stripper: SRCSStripper) -> None:
    """Write each stripped record to the current working directory."""
    for i, (hdr, secdata) in enumerate(
        zip(stripper.get_header(), stripper.get_stripped_data()),
    ):
        if hdr[0:4] == b"SRCS":
            fname = "kindlestrip_source_archive.zip"
        elif hdr[0:4] == b"CMET":
            fname = "kindlestrip_build_log.txt"
        else:
            fname = "kindlestrip_unknown%05d.dat" % i
        print("Stripped Record Type:", hdr[0:4].decode("latin-1"), " file:", fname)
        Path(fname).write_bytes(secdata)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kindlestrip",
        description=(
            "Strips the Sources (SRCS) record from Mobipocket ebooks generated "
            "using KindleGen 1.1 and later that add the source archive."
        ),
    )
    parser.add_argument(
        "-d",
        "--dump",
        action="store_true",
        help="dump stripped SRCS records to the current working directory",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"KindleStrip {__version__}",
    )
    parser.add_argument("infile", type=Path, help="input Mobipocket file")
    parser.add_argument("outfile", type=Path, help="output (stripped) file")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        data_file = args.infile.read_bytes()
        stripper = SRCSStripper(data_file)
        args.outfile.write_bytes(stripper.get_result())
        if args.dump:
            _dump_stripped_records(stripper)
    except StripException as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
