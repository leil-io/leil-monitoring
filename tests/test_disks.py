import unittest
import struct
from saunafs_client.models import Disk
from saunafs_client.deserializer import DeserializationError
from tests.test_utils import serialize_disk


class TestDiskDeserialization(unittest.TestCase):
    def test_from_buffer(self):
        path = "/mnt/disk1"
        flags = 0  # ok
        err_chunk_id = 0
        err_time = 0
        used_space = 5000
        total_space = 10000
        chunks_cnt = 100

        mock_buffer = serialize_disk(path, flags, err_chunk_id, err_time, used_space, total_space, chunks_cnt)
        buffer_copy = bytearray(mock_buffer)

        disk = Disk.from_buffer(buffer_copy)

        self.assertEqual(disk.path, path)
        self.assertEqual(disk.status, "ok")
        self.assertEqual(disk.last_error, "no errors")
        self.assertEqual(disk.used_space, used_space)
        self.assertEqual(disk.total_space, total_space)
        self.assertEqual(disk.chunks, chunks_cnt)
        self.assertEqual(len(buffer_copy), 0)

        # Test with different flags and error time
        path = "/mnt/disk2"
        flags = 2  # damaged
        err_chunk_id = 12345
        err_time = 98765
        used_space = 100
        total_space = 200
        chunks_cnt = 5

        mock_buffer = serialize_disk(path, flags, err_chunk_id, err_time, used_space, total_space, chunks_cnt)
        buffer_copy = bytearray(mock_buffer)

        disk = Disk.from_buffer(buffer_copy)

        self.assertEqual(disk.path, path)
        self.assertEqual(disk.status, "damaged")
        self.assertEqual(disk.last_error, f"{err_time} on chunk: {err_chunk_id}")
        self.assertEqual(disk.used_space, used_space)
        self.assertEqual(disk.total_space, total_space)
        self.assertEqual(disk.chunks, chunks_cnt)
        self.assertEqual(len(buffer_copy), 0)

    def test_from_buffer_deserialization_error(self):
        # Buffer too short for entry_size
        short_buffer = bytearray(struct.pack(">B", 1))  # Only 1 byte
        with self.assertRaises(DeserializationError):
            Disk.from_buffer(short_buffer)

        # Buffer too short for full entry after reading entry_size
        path = "/mnt/disk_short"
        flags = 0
        err_chunk_id = 0
        err_time = 0
        used_space = 100
        total_space = 200
        chunks_cnt = 5

        mock_buffer = serialize_disk(path, flags, err_chunk_id, err_time, used_space, total_space, chunks_cnt)
        truncated_buffer = mock_buffer[:len(mock_buffer) - 5]

        with self.assertRaises(DeserializationError):
            Disk.from_buffer(bytearray(truncated_buffer))

    def test_get_list(self):
        disk1_data = {
            "path": "/mnt/diskA", "flags": 0, "err_chunk_id": 0, "err_time": 0,
            "used_space": 1000, "total_space": 2000, "chunks_cnt": 50
        }
        disk2_data = {
            "path": "/mnt/diskB", "flags": 1, "err_chunk_id": 123, "err_time": 456,
            "used_space": 500, "total_space": 1000, "chunks_cnt": 25
        }

        mock_disk1_buffer = serialize_disk(**disk1_data)
        mock_disk2_buffer = serialize_disk(**disk2_data)

        list_buffer = bytearray()
        list_buffer.extend(mock_disk1_buffer)
        list_buffer.extend(mock_disk2_buffer)

        disks = Disk.get_list(list_buffer)

        self.assertEqual(len(disks), 2)

        # Assertions for disk 1
        self.assertEqual(disks[0].path, disk1_data['path'])
        self.assertEqual(disks[0].status, "ok")
        self.assertEqual(disks[0].last_error, "no errors")
        self.assertEqual(disks[0].used_space, disk1_data['used_space'])
        self.assertEqual(disks[0].total_space, disk1_data['total_space'])
        self.assertEqual(disks[0].chunks, disk1_data['chunks_cnt'])

        # Assertions for disk 2
        self.assertEqual(disks[1].path, disk2_data['path'])
        self.assertEqual(disks[1].status, "marked for removal")
        self.assertEqual(disks[1].last_error, f"{disk2_data['err_time']} on chunk: {disk2_data['err_chunk_id']}")
        self.assertEqual(disks[1].used_space, disk2_data['used_space'])
        self.assertEqual(disks[1].total_space, disk2_data['total_space'])
        self.assertEqual(disks[1].chunks, disk2_data['chunks_cnt'])

        self.assertEqual(len(list_buffer), 0)
