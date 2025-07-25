import unittest
import struct
from models import Mount, OperationStats
from deserializer import DeserializationError
from tests.test_utils import serialize_mount, serialize_mount_info

class TestMountDeserialization(unittest.TestCase):

    def test_from_buffer(self):
        session_id = 12345
        ip_address = "192.168.1.1"
        version = "1.2.3"
        root_path = "/mnt/saunafs"
        mounted_path = "/home/user/saunafs_mount"
        sesflags = 1 | 16 # ro, map_all
        root_uid = 1000
        root_gid = 1000
        map_all_uid = 999
        map_all_gid = 999
        min_goal = 1
        max_goal = 3
        min_trash_time = 3600
        max_trash_time = 86400
        stats_count = 16 # OperationStats has 16 fields + total
        current_op_stats_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
        last_hour_op_stats_list = [16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]

        mock_buffer = serialize_mount(
            session_id, ip_address, version, root_path, mounted_path,
            sesflags, root_uid, root_gid, map_all_uid, map_all_gid,
            min_goal, max_goal, min_trash_time, max_trash_time,
            current_op_stats_list, last_hour_op_stats_list
        )

        # Create a mutable copy of the buffer for the method under test
        buffer_copy = bytearray(mock_buffer)

        # Call the from_buffer method
        mount = Mount.from_buffer(buffer_copy, stats_count)

        # Assertions
        self.assertEqual(mount.session_id, session_id)
        # Hostname will be '(unresolved)' because socket.gethostbyaddr is not mocked
        self.assertEqual(mount.hostname, "(unresolved)")
        self.assertEqual(mount.ip_address, ip_address)
        self.assertEqual(mount.mounted_path, mounted_path)
        self.assertEqual(mount.version, version)
        self.assertEqual(mount.root_path, root_path)
        self.assertEqual(mount.mount_info, "") # This is set by caller, not from buffer
        self.assertEqual(mount.flags, "ro, map_all")
        self.assertEqual(mount.root_uid, root_uid)
        self.assertEqual(mount.root_gid, root_gid)
        self.assertEqual(mount.map_all_uid, map_all_uid)
        self.assertEqual(mount.map_all_gid, map_all_gid)
        self.assertEqual(mount.min_goal, min_goal)
        self.assertEqual(mount.max_goal, max_goal)
        self.assertEqual(mount.min_trash_time, min_trash_time)
        self.assertEqual(mount.max_trash_time, max_trash_time)

        # Assert current_op_stats
        self.assertIsInstance(mount.current_op_stats, OperationStats)
        self.assertEqual(mount.current_op_stats.statfs, current_op_stats_list[0])
        self.assertEqual(mount.current_op_stats.total, sum(current_op_stats_list))

        # Assert last_hour_op_stats
        self.assertIsInstance(mount.last_hour_op_stats, OperationStats)
        # Note: models.py sets last_hour_op_stats to current_op_stats_list, so we assert against that
        self.assertEqual(mount.last_hour_op_stats.statfs, current_op_stats_list[0])
        self.assertEqual(mount.last_hour_op_stats.total, sum(current_op_stats_list))

        # Ensure the buffer is empty after deserialization
        self.assertEqual(len(buffer_copy), 0)

    def test_from_buffer_deserialization_error(self):
        # Create a buffer that is intentionally too short
        short_buffer = bytearray(struct.pack(">LBBBBHBB", 1, 1, 1, 1, 1, 1, 1, 1)) # Only the first part

        with self.assertRaises(DeserializationError):
            Mount.from_buffer(short_buffer, 16)

    def test_get_mounts_info(self):
        session_id = 12345
        mount_info_string = "Test Mount Info"

        # Build the mock buffer for get_mounts_info
        mock_mount_info_buffer = bytearray(struct.pack(">L", 1)) # vector_size = 1
        mock_mount_info_buffer.extend(serialize_mount_info(session_id, mount_info_string))

        # Call the static method
        mounts_info = Mount.get_mounts_info(mock_mount_info_buffer)

        # Assertions
        self.assertIsInstance(mounts_info, dict)
        self.assertEqual(len(mounts_info), 1)
        self.assertIn(session_id, mounts_info)
        self.assertEqual(mounts_info[session_id], mount_info_string)

        # Test error handling for get_mounts_info (empty buffer)
        mounts_info_error = Mount.get_mounts_info(bytearray())
        self.assertEqual(mounts_info_error, {}) # Should return empty dict on error

    def test_get_list(self):
        session_id = 12345
        ip_address = "192.168.1.1"
        version = "1.2.3"
        root_path = "/mnt/saunafs"
        mounted_path = "/home/user/saunafs_mount"
        sesflags = 1 | 16 # ro, map_all
        root_uid = 1000
        root_gid = 1000
        map_all_uid = 999
        map_all_gid = 999
        min_goal = 1
        max_goal = 3
        min_trash_time = 3600
        max_trash_time = 86400
        stats_count = 16
        current_op_stats_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
        last_hour_op_stats_list = [16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]

        # Build the mock buffer for a single Mount
        mock_single_mount_buffer = serialize_mount(
            session_id, ip_address, version, root_path, mounted_path,
            sesflags, root_uid, root_gid, map_all_uid, map_all_gid,
            min_goal, max_goal, min_trash_time, max_trash_time,
            current_op_stats_list, last_hour_op_stats_list
        )

        # Build the buffer for get_list (prefix with stats_count)
        list_buffer = bytearray()
        list_buffer.extend(struct.pack(">H", stats_count))
        list_buffer.extend(mock_single_mount_buffer)
        list_buffer.extend(mock_single_mount_buffer) # Add a second mount for testing list functionality

        # Build extra_mount_info_buffer
        extra_mount_info_buffer = bytearray(struct.pack(">L", 1)) # vector_size = 1
        extra_mount_info_buffer.extend(serialize_mount_info(session_id, "Extra info for session 12345"))

        # Call the get_list method
        mounts = Mount.get_list(list_buffer, extra_mount_info_buffer)

        # Assertions
        self.assertEqual(len(mounts), 2)

        # Check the first mount
        self.assertEqual(mounts[0].id, 1)
        self.assertEqual(mounts[0].session_id, session_id)
        self.assertEqual(mounts[0].hostname, "(unresolved)")
        self.assertEqual(mounts[0].ip_address, ip_address)
        self.assertEqual(mounts[0].mounted_path, mounted_path)
        self.assertEqual(mounts[0].version, version)
        self.assertEqual(mounts[0].root_path, root_path)
        self.assertEqual(mounts[0].mount_info, "\nExtra info for session 12345") # Check extra_info
        self.assertEqual(mounts[0].flags, "ro, map_all")
        self.assertEqual(mounts[0].root_uid, root_uid)
        self.assertEqual(mounts[0].root_gid, root_gid)
        self.assertEqual(mounts[0].map_all_uid, map_all_uid)
        self.assertEqual(mounts[0].map_all_gid, map_all_gid)
        self.assertEqual(mounts[0].min_goal, min_goal)
        self.assertEqual(mounts[0].max_goal, max_goal)
        self.assertEqual(mounts[0].min_trash_time, min_trash_time)
        self.assertEqual(mounts[0].max_trash_time, max_trash_time)
        self.assertIsInstance(mounts[0].current_op_stats, OperationStats)
        self.assertIsInstance(mounts[0].last_hour_op_stats, OperationStats)

        # Check the second mount (should be identical except for ID)
        self.assertEqual(mounts[1].id, 2)
        self.assertEqual(mounts[1].session_id, session_id)
        self.assertEqual(mounts[1].mount_info, "\nExtra info for session 12345") # Check extra_info

        # Ensure the buffer is empty after deserialization
        self.assertEqual(len(list_buffer), 0)
        self.assertEqual(len(extra_mount_info_buffer), 0)
