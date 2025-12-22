"""
This file is part of saunafs-monitoring.
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
from saunafs_client.models import Metalogger
from saunafs_client.deserializer import DeserializationError
from tests.test_utils import serialize_metalogger


class TestMetaloggerDeserialization(unittest.TestCase):

    def test_from_buffer(self):
        version = "1.0.0"
        ip_address = "10.0.0.1"

        mock_buffer = serialize_metalogger(version, ip_address)
        buffer_copy = bytearray(mock_buffer)

        metalogger = Metalogger.from_buffer(buffer_copy)

        self.assertEqual(metalogger.id, 0)  # ID is set by caller
        self.assertEqual(metalogger.hostname, "(unresolved)")  # socket.gethostbyaddr not mocked
        self.assertEqual(metalogger.ip_address, ip_address)
        self.assertEqual(metalogger.version, version)

        self.assertEqual(len(buffer_copy), 0)

    def test_from_buffer_deserialization_error(self):
        # Buffer too short
        short_buffer = bytearray(struct.pack(">HBB", 1, 0, 0))  # Incomplete data

        with self.assertRaises(DeserializationError):
            Metalogger.from_buffer(short_buffer)

    def test_get_list(self):
        version1 = "1.0.0"
        ip_address1 = "10.0.0.1"
        version2 = "1.0.1"
        ip_address2 = "10.0.0.2"

        mock_metalogger1_buffer = serialize_metalogger(version1, ip_address1)
        mock_metalogger2_buffer = serialize_metalogger(version2, ip_address2)

        list_buffer = bytearray()
        list_buffer.extend(mock_metalogger1_buffer)
        list_buffer.extend(mock_metalogger2_buffer)

        metaloggers = Metalogger.get_list(list_buffer)

        self.assertEqual(len(metaloggers), 2)

        self.assertEqual(metaloggers[0].id, 1)
        self.assertEqual(metaloggers[0].hostname, "(unresolved)")
        self.assertEqual(metaloggers[0].ip_address, ip_address1)
        self.assertEqual(metaloggers[0].version, version1)

        self.assertEqual(metaloggers[1].id, 2)
        self.assertEqual(metaloggers[1].hostname, "(unresolved)")
        self.assertEqual(metaloggers[1].ip_address, ip_address2)
        self.assertEqual(metaloggers[1].version, version2)

        self.assertEqual(len(list_buffer), 0)
