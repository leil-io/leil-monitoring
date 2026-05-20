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
from leil_client.models import Export
from leil_client.deserializer import DeserializationError
from tests.test_utils import serialize_export


class TestExportDeserialization(unittest.TestCase):

    def test_from_buffer(self):
        ip_from = "192.168.1.1"
        ip_to = "192.168.1.255"
        path = "/export/path"
        version = "1.0.0"
        exportflags = 0
        sesflags = 1  # ro
        root_uid = 1000
        root_gid = 1000
        map_all_uid = 65534
        map_all_gid = 65534

        mock_buffer = serialize_export(
            ip_from, ip_to, path, version, exportflags, sesflags,
            root_uid, root_gid, map_all_uid, map_all_gid
        )
        buffer_copy = bytearray(mock_buffer)
        export = Export.from_buffer(buffer_copy)

        self.assertEqual(export.id, 0)  # ID is set by caller
        self.assertEqual(export.ip_from, ip_from)
        self.assertEqual(export.ip_to, ip_to)
        self.assertEqual(export.path, path)
        self.assertEqual(export.flags, "ro")

        self.assertEqual(len(buffer_copy), 0)

    def test_from_buffer_deserialization_error(self):
        # Buffer too short for initial fields
        short_buffer = bytearray(struct.pack(">BBBB", 1, 2, 3, 4))  # Only part of ip_from
        with self.assertRaises(DeserializationError):
            Export.from_buffer(short_buffer)

        # Buffer too short for path
        ip_from = "192.168.1.1"
        ip_to = "192.168.1.255"
        path = "/a_very_long_export_path_that_will_make_the_buffer_short_if_not_fully_included"
        version = "1.0.0"
        exportflags = 0
        sesflags = 1
        root_uid = 1000
        root_gid = 1000
        map_all_uid = 65534
        map_all_gid = 65534

        mock_buffer_full = serialize_export(
            ip_from, ip_to, path, version, exportflags, sesflags,
            root_uid, root_gid, map_all_uid, map_all_gid
        )
        # Truncate the buffer to be too short for the full path
        mock_buffer_incomplete_path = mock_buffer_full[: len(mock_buffer_full) - (len(path.encode('utf-8')) // 2)]

        with self.assertRaises(DeserializationError):
            Export.from_buffer(bytearray(mock_buffer_incomplete_path))

        # Buffer too short for final fields (version, flags, uids/gids)
        ip_from = "192.168.1.1"
        ip_to = "192.168.1.255"
        path = "/short/path"
        version = "1.0.0"
        exportflags = 0
        sesflags = 1
        root_uid = 1000
        root_gid = 1000
        map_all_uid = 65534
        map_all_gid = 65534

        mock_buffer_full = serialize_export(
            ip_from, ip_to, path, version, exportflags, sesflags,
            root_uid, root_gid, map_all_uid, map_all_gid
        )
        # Truncate the buffer to be too short for the final struct unpack
        mock_buffer_incomplete_final = mock_buffer_full[: len(mock_buffer_full) - 10]  # Arbitrary truncation

        with self.assertRaises(DeserializationError):
            Export.from_buffer(bytearray(mock_buffer_incomplete_final))

    def test_get_list(self):
        export1_data = {
            "ip_from": "10.0.0.1", "ip_to": "10.0.0.10", "path": "/export1",
            "version": "1.0.0", "exportflags": 0, "sesflags": 1, "root_uid": 0, "root_gid": 0,
            "map_all_uid": 65534, "map_all_gid": 65534
        }
        export2_data = {
            "ip_from": "10.0.0.11", "ip_to": "10.0.0.20", "path": "/export2",
            "version": "1.0.1", "exportflags": 0, "sesflags": 16, "root_uid": 100, "root_gid": 100,
            "map_all_uid": 0, "map_all_gid": 0
        }

        mock_export1_buffer = serialize_export(**export1_data)
        mock_export2_buffer = serialize_export(**export2_data)

        list_buffer = bytearray()
        list_buffer.extend(mock_export1_buffer)
        list_buffer.extend(mock_export2_buffer)

        exports = Export.get_list(list_buffer)

        self.assertEqual(len(exports), 2)

        # Assertions for export 1
        self.assertEqual(exports[0].id, 1)
        self.assertEqual(exports[0].ip_from, export1_data['ip_from'])
        self.assertEqual(exports[0].ip_to, export1_data['ip_to'])
        self.assertEqual(exports[0].path, export1_data['path'])
        self.assertEqual(exports[0].flags, "ro")

        # Assertions for export 2
        self.assertEqual(exports[1].id, 2)
        self.assertEqual(exports[1].ip_from, export2_data['ip_from'])
        self.assertEqual(exports[1].ip_to, export2_data['ip_to'])
        self.assertEqual(exports[1].path, export2_data['path'])
        self.assertEqual(exports[1].flags, "rw, map_all")

        self.assertEqual(len(list_buffer), 0)
