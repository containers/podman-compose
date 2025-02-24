# SPDX-License-Identifier: GPL-2.0
# pylint: disable=protected-access

import io
import unittest

from podman_compose import Podman


class DummyReader:
    def __init__(self, data=None):
        self.data = data or []

    async def readuntil(self, _):
        return self.data.pop(0)

    def at_eof(self):
        return len(self.data) == 0


class TestComposeRunLogFormat(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.p = get_minimal_podman()
        self.buffer = io.StringIO()

    async def test_single_line_single_chunk(self):
        reader = DummyReader([b'hello, world\n'])
        await self.p._format_stream(reader, self.buffer, 'LL:')
        self.assertEqual(self.buffer.getvalue(), 'LL: hello, world\n')

    async def test_empty_line(self):
        reader = DummyReader([b'\n'])
        await self.p._format_stream(reader, self.buffer, 'LL:')
        self.assertEqual(self.buffer.getvalue(), 'LL: \n')

    async def test_line_split(self):
        reader = DummyReader([b'hello,', b' world\n'])
        await self.p._format_stream(reader, self.buffer, 'LL:')
        self.assertEqual(self.buffer.getvalue(), 'LL: hello, world\n')

    async def test_two_lines_in_one_chunk(self):
        reader = DummyReader([b'hello\nbye\n'])
        await self.p._format_stream(reader, self.buffer, 'LL:')
        self.assertEqual(self.buffer.getvalue(), 'LL: hello\nLL: bye\n')

    async def test_double_blank(self):
        reader = DummyReader([b'hello\n\n\nbye\n'])
        await self.p._format_stream(reader, self.buffer, 'LL:')
        self.assertEqual(self.buffer.getvalue(), 'LL: hello\nLL: \nLL: \nLL: bye\n')

    async def test_no_new_line_at_end(self):
        reader = DummyReader([b'hello\nbye'])
        await self.p._format_stream(reader, self.buffer, 'LL:')
        self.assertEqual(self.buffer.getvalue(), 'LL: hello\nLL: bye\n')


def get_minimal_podman():
    return Podman(None)
