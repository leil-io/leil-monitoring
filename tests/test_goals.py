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
from leil_client.models import Goal
from tests.test_utils import serialize_string
from leil_client.deserializer import DeserializationError


def serialize_goal(
    id: int,
    name: str,
    definition: str,
) -> bytearray:
    """
    Serializes Disk data into a bytearray buffer for testing.
    Mirrors the Disk.from_buffer logic.
    """
    buffer = bytearray()

    buffer.extend(struct.pack(">H", id))
    buffer.extend(serialize_string(name))
    buffer.extend(serialize_string(definition))

    return buffer


class TestGoalDeserialization(unittest.TestCase):
    def test_from_buffer(self):
        id = 10
        name = "ec32"
        definition = "ec32: $ec(3,2) {_ _ _ _ _}"

        mock_buffer = serialize_goal(id, name, definition)
        buffer_copy = bytearray(mock_buffer)

        goal = Goal.from_buffer(buffer_copy)

        self.assertEqual(goal.id, id)
        self.assertEqual(goal.name, name)
        self.assertEqual(goal.definition, definition)
        self.assertEqual(len(buffer_copy), 0)

    def test_from_buffer_deserialization_error(self):
        short_buffer = bytearray(struct.pack(">H", 1))  # Only id
        with self.assertRaises(DeserializationError):
            Goal.from_buffer(short_buffer)

    def test_get_list(self):
        goal1_data = {
            "id": 1, "name": "ec32",
            "definition": "ec32: $ec(3,2) {_ _ _ _ _}"
        }
        goal2_data = {
            "id": 1, "name": "ec32",
            "definition": "ec62: $ec(6,2) {_ _ _ _ _ _ _ _}"
        }

        mock_goal1_buffer = serialize_goal(**goal1_data)
        mock_goal2_buffer = serialize_goal(**goal2_data)

        list_buffer = bytearray()
        list_buffer.extend(struct.pack(">L", 2))  # Vector length
        list_buffer.extend(mock_goal1_buffer)
        list_buffer.extend(mock_goal2_buffer)

        goals = Goal.get_list(list_buffer)

        self.assertEqual(len(goals), 2)

        # Assertions for goal 1
        self.assertEqual(goals[0].id, goal1_data['id'])
        self.assertEqual(goals[0].name, goal1_data['name'])
        self.assertEqual(goals[0].definition, goal1_data['definition'])

        # Assertions for disk 2
        self.assertEqual(goals[1].id, goal2_data['id'])
        self.assertEqual(goals[1].name, goal2_data['name'])
        self.assertEqual(goals[1].definition, goal2_data['definition'])

        self.assertEqual(len(list_buffer), 0)
