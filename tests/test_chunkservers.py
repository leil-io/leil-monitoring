import unittest
import struct
from unittest.mock import patch
from models import Server
from deserializer import DeserializationError
from tests.test_utils import serialize_server


class TestServerDeserialization(unittest.TestCase):

    @patch('socket.gethostbyaddr', return_value=('mocked-hostname', [], []))
    def test_from_buffer(self, mock_gethostbyaddr):
        is_disconnected = False
        version = "1.0.0"
        ip_address = "10.0.0.1"
        port = 9000
        used_space = 1024
        total_space = 2048
        chunks = 10
        used_space_tobedeleted = 50
        total_space_tobedeleted = 100
        chunks_tobedeleted = 5
        error_count = 0
        label = "TestServer"

        mock_buffer = serialize_server(
            is_disconnected, version, ip_address, port, used_space, total_space,
            chunks, used_space_tobedeleted, total_space_tobedeleted, chunks_tobedeleted,
            error_count, label
        )
        buffer_copy = bytearray(mock_buffer)

        server = Server.from_buffer(buffer_copy)

        self.assertEqual(server.id, 0)  # ID is set by caller
        self.assertEqual(server.hostname, "mocked-hostname")
        self.assertEqual(server.ip_address, ip_address)
        self.assertEqual(server.port, port)
        self.assertEqual(server.version, version)
        self.assertEqual(server.is_disconnected, is_disconnected)
        self.assertEqual(server.label, label)
        self.assertEqual(server.used_space, used_space)
        self.assertEqual(server.total_space, total_space)
        self.assertEqual(server.chunks, chunks)
        self.assertEqual(server.used_space_tobedeleted, used_space_tobedeleted)
        self.assertEqual(server.total_space_tobedeleted, total_space_tobedeleted)
        self.assertEqual(server.chunks_tobedeleted, chunks_tobedeleted)
        self.assertEqual(server.error_count, error_count)

        self.assertEqual(len(buffer_copy), 0)

    def test_from_buffer_deserialization_error(self):
        # Buffer too short for basic fields
        short_buffer = bytearray(struct.pack(">B", 0))  # Just disconnected flag
        with self.assertRaises(DeserializationError):
            Server.from_buffer(short_buffer)

        # Buffer too short for label
        version = "1.0.0"
        ip_address = "10.0.0.1"
        port = 9000
        used_space = 1024
        total_space = 2048
        chunks = 10
        used_space_tobedeleted = 50
        total_space_tobedeleted = 100
        chunks_tobedeleted = 5
        error_count = 0
        label = "A_very_long_label_that_will_make_the_buffer_short_if_not_fully_included"

        # Create a buffer that is too short for the full label
        mock_buffer_incomplete_label = serialize_server(
            False, version, ip_address, port, used_space, total_space,
            chunks, used_space_tobedeleted, total_space_tobedeleted, chunks_tobedeleted,
            error_count, label
        )[: - (len(label.encode('utf-8')) // 2)]  # Truncate half the label

        with self.assertRaises(DeserializationError):
            Server.from_buffer(bytearray(mock_buffer_incomplete_label))

    @patch('socket.gethostbyaddr', side_effect=lambda ip: ('mocked-hostname-' + ip, [], []))
    def test_get_list(self, mock_gethostbyaddr):
        server1_data = {
            "is_disconnected": False, "version": "1.0.0", "ip_address": "10.0.0.1",
            "port": 9000, "used_space": 100, "total_space": 200, "chunks": 10,
            "used_space_tobedeleted": 1, "total_space_tobedeleted": 2, "chunks_tobedeleted": 0,
            "error_count": 0, "label": "ServerOne"
        }
        server2_data = {
            "is_disconnected": True, "version": "1.0.1", "ip_address": "10.0.0.2",
            "port": 9001, "used_space": 150, "total_space": 300, "chunks": 15,
            "used_space_tobedeleted": 5, "total_space_tobedeleted": 10, "chunks_tobedeleted": 1,
            "error_count": 1, "label": "ServerTwo"
        }

        mock_server1_buffer = serialize_server(**server1_data)
        mock_server2_buffer = serialize_server(**server2_data)

        list_buffer = bytearray()
        list_buffer.extend(struct.pack(">L", 2))  # length of vector
        list_buffer.extend(mock_server1_buffer)
        list_buffer.extend(mock_server2_buffer)

        servers = Server.get_list(list_buffer)

        self.assertEqual(len(servers), 2)

        # Assertions for server 1
        self.assertEqual(servers[0].id, 1)
        self.assertEqual(servers[0].hostname, f"mocked-hostname-{server1_data['ip_address']}")
        self.assertEqual(servers[0].ip_address, server1_data['ip_address'])
        self.assertEqual(servers[0].port, server1_data['port'])
        self.assertEqual(servers[0].version, server1_data['version'])
        self.assertEqual(servers[0].is_disconnected, server1_data['is_disconnected'])
        self.assertEqual(servers[0].label, server1_data['label'])
        self.assertEqual(servers[0].used_space, server1_data['used_space'])
        self.assertEqual(servers[0].total_space, server1_data['total_space'])
        self.assertEqual(servers[0].chunks, server1_data['chunks'])
        self.assertEqual(servers[0].used_space_tobedeleted, server1_data['used_space_tobedeleted'])
        self.assertEqual(servers[0].total_space_tobedeleted, server1_data['total_space_tobedeleted'])
        self.assertEqual(servers[0].chunks_tobedeleted, server1_data['chunks_tobedeleted'])
        self.assertEqual(servers[0].error_count, server1_data['error_count'])

        # Assertions for server 2
        self.assertEqual(servers[1].id, 2)
        self.assertEqual(servers[1].hostname, f"mocked-hostname-{server2_data['ip_address']}")
        self.assertEqual(servers[1].ip_address, server2_data['ip_address'])
        self.assertEqual(servers[1].port, server2_data['port'])
        self.assertEqual(servers[1].version, server2_data['version'])
        self.assertEqual(servers[1].is_disconnected, server2_data['is_disconnected'])
        self.assertEqual(servers[1].label, server2_data['label'])
        self.assertEqual(servers[1].used_space, server2_data['used_space'])
        self.assertEqual(servers[1].total_space, server2_data['total_space'])
        self.assertEqual(servers[1].chunks, server2_data['chunks'])
        self.assertEqual(servers[1].used_space_tobedeleted, server2_data['used_space_tobedeleted'])
        self.assertEqual(servers[1].total_space_tobedeleted, server2_data['total_space_tobedeleted'])
        self.assertEqual(servers[1].chunks_tobedeleted, server2_data['chunks_tobedeleted'])
        self.assertEqual(servers[1].error_count, server2_data['error_count'])

        self.assertEqual(len(list_buffer), 0)
