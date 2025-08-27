import unittest
import struct
from saunafs_client.models import FsCheckInfo
from saunafs_client.deserializer import DeserializationError
from tests.test_utils import serialize_fscheck_info


class TestFsCheckInfoDeserialization(unittest.TestCase):
    def test_from_buffer(self):
        loop_start = 100
        loop_end = 200
        files = 1000
        under_goal_files = 50
        missing_files = 10
        chunks = 2000
        under_goal_chunks = 100
        missing_chunks = 20
        message = "FsCheck completed successfully."

        mock_buffer = serialize_fscheck_info(
            loop_start,
            loop_end,
            files,
            under_goal_files,
            missing_files,
            chunks,
            under_goal_chunks,
            missing_chunks,
            message,
        )
        buffer_copy = bytearray(mock_buffer)

        info = FsCheckInfo.from_buffer(buffer_copy)

        self.assertEqual(info.loop_start, loop_start)
        self.assertEqual(info.loop_end, loop_end)
        self.assertEqual(info.files, files)
        self.assertEqual(info.under_goal_files, under_goal_files)
        self.assertEqual(info.missing_files, missing_files)
        self.assertEqual(info.chunks, chunks)
        self.assertEqual(info.under_goal_chunks, under_goal_chunks)
        self.assertEqual(info.missing_chunks, missing_chunks)
        self.assertEqual(info.message, message)

        self.assertEqual(len(buffer_copy), 0)

    def test_from_buffer_deserialization_error(self):
        buffer = struct.pack(">H", 0)  # An invalid buffer for FsCheckInfo
        with self.assertRaises(DeserializationError):
            FsCheckInfo.from_buffer(buffer)

