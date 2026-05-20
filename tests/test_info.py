"""
This file is part of leil-monitoring.
Copyright (C) 2025 Leil Storage OÜ

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import unittest
import struct
from leil_client.models import SystemInfo
from leil_client.deserializer import DeserializationError
from tests.test_utils import serialize_info


class TestInfoDeserialization(unittest.TestCase):
    def test_from_buffer(self):
        version = "5.0.0"
        ram_used = 100024
        total_space = 12345
        avail_space = 1234
        trash_space = 123
        trash_files = 5000
        reserved_space = 500
        reserved_files = 450
        total_objects = 3
        directories = 1
        files = 1
        symlinks = 1
        chunks = 4
        all_copies = 4
        regular_copies = 4

        mock_buffer = serialize_info(
            version,
            ram_used,
            total_space,
            avail_space,
            trash_space,
            trash_files,
            reserved_space,
            reserved_files,
            total_objects,
            directories,
            files,
            symlinks,
            chunks,
            all_copies,
            regular_copies,
        )
        buffer_copy = bytearray(mock_buffer)

        info = SystemInfo.from_buffer(buffer_copy)

        self.assertEqual(info.version, version)
        self.assertEqual(info.ram_used, ram_used)
        self.assertEqual(info.total_space, total_space)
        self.assertEqual(info.avail_space, avail_space)
        self.assertEqual(info.trash_space, trash_space)
        self.assertEqual(info.trash_files, trash_files)
        self.assertEqual(info.reserved_space, reserved_space)
        self.assertEqual(info.reserved_files, reserved_files)
        self.assertEqual(info.total_objects, total_objects)
        self.assertEqual(info.directories, directories)
        self.assertEqual(info.files, files)
        self.assertEqual(info.symlinks, symlinks)
        self.assertEqual(info.chunks, chunks)
        self.assertEqual(info.all_copies, all_copies)
        self.assertEqual(info.all_copies, regular_copies)

        self.assertEqual(len(buffer_copy), 0)

    def test_from_buffer_deserialization_error(self):
        buffer = struct.pack(">H", 0)
        with self.assertRaises(DeserializationError):
            SystemInfo.from_buffer(buffer)
