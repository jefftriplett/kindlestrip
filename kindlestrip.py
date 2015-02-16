#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
#
# This is a python script. You need a Python interpreter to run it.
# For example, ActiveState Python, which exists for windows.
#
# This script strips the penultimate record from a Mobipocket file.
# This is useful because the current KindleGen add a compressed copy
# of the source files used in this record, making the ebook produced
# about twice as big as it needs to be.
#
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

__version__ = '1.36.0'

import codecs
import getopt
import locale
import os
import struct
import sys


iswindows = sys.platform.startswith('win')

# Because Windows (and Mac OS X) allows full unicode filenames and paths
# any paths in pure bytestring python 2.X code must be utf-8 encoded as they will need to
# be converted on the fly to full unicode for Windows platforms.  Any other 8-bit str
# encoding would lose characters that can not be represented in that encoding
# these are simple support routines to allow use of utf-8 encoded bytestrings as paths in main program
# to be converted on the fly to full unicode as temporary un-named values to prevent
# the potential mixing of unicode and bytestring string values in the main program

def pathof(s):
    if isinstance(s, unicode):
        print "Warning: pathof expects utf-8 encoded byestring: ", s
        if iswindows:
            return s
        return s.encode('utf-8')
    if iswindows:
        return s.decode('utf-8')
    return s

# force string to be utf-8 encoded whether unicode or bytestring
def utf8_str(p, enc='utf-8'):
    if isinstance(p, unicode):
        return p.encode('utf-8')
    if enc != 'utf-8':
        return p.decode(enc).encode('utf-8')
    return p

# get sys.argv arguments and encode them into utf-8
def utf8_argv():
    global iswindows
    if iswindows:
        # Versions 2.x of Python don't support Unicode in sys.argv on
        # Windows, with the underlying Windows API instead replacing multi-byte
        # characters with '?'.  So use shell32.GetCommandLineArgvW to get sys.argv
        # as a list of Unicode strings and encode them as utf-8

        from ctypes import POINTER, byref, cdll, c_int, windll
        from ctypes.wintypes import LPCWSTR, LPWSTR

        GetCommandLineW = cdll.kernel32.GetCommandLineW
        GetCommandLineW.argtypes = []
        GetCommandLineW.restype = LPCWSTR

        CommandLineToArgvW = windll.shell32.CommandLineToArgvW
        CommandLineToArgvW.argtypes = [LPCWSTR, POINTER(c_int)]
        CommandLineToArgvW.restype = POINTER(LPWSTR)

        cmd = GetCommandLineW()
        argc = c_int(0)
        argv = CommandLineToArgvW(cmd, byref(argc))
        if argc.value > 0:
            # Remove Python executable and commands if present
            start = argc.value - len(sys.argv)
            return [argv[i].encode('utf-8') for i in
                    xrange(start, argc.value)]
        # this should never happen
        return None
    else:
        argv = []
        argvencoding = sys.stdin.encoding
        if argvencoding == None:
            argvencoding = sys.getfilesystemencoding()
        if argvencoding == None:
            argvencoding = 'utf-8'
        for arg in sys.argv:
            if type(arg) == unicode:
                argv.append(arg.encode('utf-8'))
            else:
                argv.append(arg.decode(argvencoding).encode('utf-8'))
        return argv


# Python 2.X is broken in that it does not recognize CP65001 as UTF-8
def add_cp65001_codec():
    try:
        codecs.lookup('cp65001')
    except LookupError:
        codecs.register(
            lambda name: name == 'cp65001' and codecs.lookup('utf-8') or None)
    return

# Almost all sane operating systems now default to utf-8 (or full unicode) as the
# proper default encoding so that all files and path names
# in any language can be properly represented.

def set_utf8_default_encoding():
    if sys.getdefaultencoding() in ['utf-8', 'UTF-8','cp65001','CP65001']:
        return

    # Regenerate setdefaultencoding.
    reload(sys)
    sys.setdefaultencoding('utf-8')

    for attr in dir(locale):
        if attr[0:3] != 'LC_':
            continue
        aref = getattr(locale, attr)
        try:
            locale.setlocale(aref, '')
        except locale.Error:
            continue
        try:
            lang = locale.getlocale(aref)[0]
        except (TypeError, ValueError):
            continue
        if lang:
            try:
                locale.setlocale(aref, (lang, 'UTF-8'))
            except locale.Error:
                os.environ[attr] = lang + '.UTF-8'
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        pass
    return

class Unbuffered:
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
    def __getattr__(self, attr):
        return getattr(self.stream, attr)


class StripException(Exception):
    pass


def patchdata(datain, off, new):
    dout=[]
    dout.append(datain[:off])
    dout.append(new)
    dout.append(datain[off+len(new):])
    return ''.join(dout)

def joindata(datain, new):
    dout=[]
    dout.append(datain)
    dout.append(new)
    return ''.join(dout)


class SRCSStripper:

    def sec_info(self, secnum):
        start_offset, flgval = struct.unpack_from('>2L', self.datain, 78+(secnum*8))
        if secnum == self.num_sections:
            next_offset = len(self.datain)
        else:
            next_offset, nflgval = struct.unpack_from('>2L', self.datain, 78+((secnum+1)*8))
        return start_offset, flgval, next_offset

    def loadSection(self, secnum):
        start_offset, tval, next_offset = self.sec_info(secnum)
        return self.datain[start_offset: next_offset]


    def __init__(self, datain):
        if datain[0x3C:0x3C+8] != 'BOOKMOBI':
            raise StripException("invalid file format")
        self.datain = datain
        self.num_sections, = struct.unpack('>H', datain[76:78])

        # get mobiheader
        mobiheader = self.loadSection(0)

        # get SRCS section number and count
        self.srcs_secnum, self.srcs_cnt = struct.unpack_from('>2L', mobiheader, 0xe0)
        if self.srcs_secnum == 0xffffffff or self.srcs_cnt == 0:
            raise StripException("File doesn't contain the sources section.")

        print "SRCS section number is: ", self.srcs_secnum
        print "SRCS section count is: ", self.srcs_cnt


        # store away srcs sections in case the user wants them later
        self.srcs_headers = []
        self.srcs_data = []
        for i in xrange(self.srcs_secnum, self.srcs_secnum + self.srcs_cnt):
            data = self.loadSection(i)
            self.srcs_headers.append(data[0:16])
            self.srcs_data.append(data[16:])

        # find its SRCS region starting offset and total length
        self.srcs_offset, fval, temp2 = self.sec_info(self.srcs_secnum)
        next = self.srcs_secnum + self.srcs_cnt
        next_offset, temp1, temp2 = self.sec_info(next)
        self.srcs_length = next_offset - self.srcs_offset
        print "SRCS length is: 0x%x" %  self.srcs_length

        if self.datain[self.srcs_offset:self.srcs_offset+4] != 'SRCS':
            raise StripException("SRCS section num does not point to SRCS.")

        # first write out the number of sections
        self.data_file = self.datain[:76]
        self.data_file = joindata(self.data_file, struct.pack('>H',self.num_sections))

        # we are going to make the SRCS section lengths all  be 0
        # offsets up to and including the first srcs record must not be changed
        last_offset = -1
        for i in xrange(self.srcs_secnum+1):
            offset, flgval, temp  = self.sec_info(i)
            last_offset = offset
            self.data_file = joindata(self.data_file, struct.pack('>L',offset) + struct.pack('>L',flgval))
            # print "section: %d, offset %0x, flgval %0x" % (i, offset, flgval)

        # for every additional record in SRCS records set start to last_offset (they are all zero length)
        for i in xrange(self.srcs_secnum + 1, self.srcs_secnum + self.srcs_cnt):
            temp1, flgval, temp2 = self.sec_info(i)
            self.data_file = joindata(self.data_file, struct.pack('>L',last_offset) + struct.pack('>L',flgval))
            # print "section: %d, offset %0x, flgval %0x" % (i, last_offset, flgval)

        # for every record after the SRCS records we must start it earlier by an amount
        # equal to the total length of all of the SRCS section
        delta = 0 - self.srcs_length
        for i in xrange(self.srcs_secnum + self.srcs_cnt , self.num_sections):
            offset, flgval, temp = self.sec_info(i)
            offset += delta
            self.data_file = joindata(self.data_file, struct.pack('>L',offset) + struct.pack('>L',flgval))
            # print "section: %d, offset %0x, flgval %0x" % (i, offset, flgval)

        # now pad it out to begin right at the first offset
        # typically this is 2 bytes of nulls
        first_offset, flgval = struct.unpack_from('>2L', self.data_file, 78)
        self.data_file = joindata(self.data_file, '\0' * (first_offset - len(self.data_file)))

        # now add on every thing up to the original src_offset and then everything after it
        dout = []
        dout.append(self.data_file)
        dout.append(self.datain[first_offset: self.srcs_offset])
        dout.append(self.datain[self.srcs_offset+self.srcs_length:])
        self.data_file = "".join(dout)

        # update the srcs_secnum and srcs_cnt in the new mobiheader
        offset0, flgval0 = struct.unpack_from('>2L', self.data_file, 78)
        offset1, flgval1 = struct.unpack_from('>2L', self.data_file, 86)
        mobiheader = self.data_file[offset0:offset1]
        mobiheader = mobiheader[:0xe0]+ struct.pack('>L', 0xffffffff) + struct.pack('>L', 0) + mobiheader[0xe8:]
        self.data_file = patchdata(self.data_file, offset0, mobiheader)
        print "done"

    def getResult(self):
        return self.data_file

    def getStrippedData(self):
        return self.srcs_data

    def getHeader(self):
        return self.srcs_headers


def usage(progname):
    print ('KindleStrip v%(__version__)s. '
       'Written 2010-2012 by Paul Durrant and Kevin Hendricks.' % globals())
    print "Strips the Sources record from Mobipocket ebooks"
    print "For ebooks generated using KindleGen 1.1 and later that add the source"
    print "Usage:"
    print "    %s [Options] <infile> <outfile>" % progname
    print "Options: "
    print " -h  print this help message "
    print " -d  dump stripped SRCS records to the current working directory "


def main(argv=utf8_argv()):
    progname = os.path.basename(argv[0])
    DUMPSRCS = False
    try:
        opts, args = getopt.getopt(argv[1:], "hd")
    except getopt.GetoptError, err:
        print str(err)
        usage(progname)
        return 2

    if len(args) != 2:
        usage(progname)
        return 1

    for o, a in opts:
        if o == "-h":
            usage(progname)
            sys.exit(0)
        if o == "-d":
            DUMPSRCS = True

    infile = args[0]
    outfile = args[1]
    try:
        data_file = file(pathof(infile), 'rb').read()
        strippedFile = SRCSStripper(data_file)
        file(pathof(outfile), 'wb').write(strippedFile.getResult())
        if DUMPSRCS:
            headers = strippedFile.getHeader()
            secdatas = strippedFile.getStrippedData()
            for i in xrange(0, len(headers)):
                hdr = headers[i]
                secdata = secdatas[i]
                if hdr[0:4] == "SRCS":
                    fname = "kindlestrip_source_archive.zip"
                elif hdr[0:4] == "CMET":
                    fname = "kindlestrip_build_log.txt"
                else:
                    fname = "kindlestrip_unknown%05d.dat" % i
                print "Stripped Record Type: ", hdr[0:4], " file: ", fname
                fname = "./" + fname
                file(pathof(fname), 'wb').write(secdata)

    except StripException, e:
        print "Error: %s" % e
        return 1
    return 0


def cli_main():
    add_cp65001_codec()
    set_utf8_default_encoding()
    sys.exit(main())


if __name__ == '__main__':
    cli_main()
