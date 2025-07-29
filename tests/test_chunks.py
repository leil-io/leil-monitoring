import unittest
import struct
import random
from models import ChunkHealth
from deserializer import DeserializationError


def serialize_chunk_health(regular_only, safe, endangered, lost, replication, deletion) -> bytearray:
    """
    Serialize chunk health data into binary format.

    Arguments:
    - regular_only (bool)
    - safe, endangered, lost: dict(goal_id -> uint64 count)
    - replication, deletion: dict(goal_id -> tuple of 11 uint64)

    Returns:
    - bytes: bytearray payload
    """
    data = bytearray()

    # 1 byte: regular_only
    data += struct.pack(">B", 1 if regular_only else 0)

    # helper for dict(goal_id -> uint64)
    def write_simple_dict(d):
        data.extend(struct.pack(">L", len(d)))
        for goal_id, value in d.items():
            data.extend(struct.pack(">B Q", goal_id, value))

    # helper for dict(goal_id -> 11x uint64)
    def write_complex_dict(d):
        data.extend(struct.pack(">L", len(d)))
        for goal_id, values in d.items():
            if len(values) != 11:
                raise ValueError("Replication/Deletion tuples must have exactly 11 values")
            data.extend(struct.pack(">B 11Q", goal_id, *values))

    write_simple_dict(safe)
    write_simple_dict(endangered)
    write_simple_dict(lost)
    write_complex_dict(replication)
    write_complex_dict(deletion)

    return data


class TestChunkHealthDeserialization(unittest.TestCase):
    def test_from_buffer(self):
        safe = {1: 100, 2: 200}
        endangered = {1: 5, 2: 1}
        lost = {2: 2}
        replication = {
            1: tuple(random.randint(0, 50) for _ in range(11)),
            2: tuple(random.randint(0, 50) for _ in range(11))
        }
        deletion = {
            1: tuple(random.randint(0, 10) for _ in range(11)),
            2: tuple(random.randint(0, 10) for _ in range(11))
        }
        chunk_buffer = serialize_chunk_health(False, safe, endangered, lost, replication, deletion)
        health = ChunkHealth.from_buffer(chunk_buffer)

        self.assertEqual(health.safe[1], safe[1])
        self.assertEqual(health.safe[2], safe[2])
        self.assertEqual(health.endangered[1], endangered[1])
        self.assertEqual(health.endangered[2], endangered[2])
        self.assertEqual(health.lost[2], lost[2])
        self.assertEqual(health.replication[1], list(replication[1]))
        self.assertEqual(health.replication[2], list(replication[2]))
        self.assertEqual(health.deletion[1], list(deletion[1]))
        self.assertEqual(health.deletion[2], list(deletion[2]))

    def test_from_buffer_deserialization_error(self):
        short_buffer = bytearray(struct.pack(">B", 1))  # Only regular_only
        with self.assertRaises(DeserializationError):
            ChunkHealth.from_buffer(short_buffer)
