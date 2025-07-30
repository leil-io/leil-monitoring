import unittest
import struct
import ipaddress
from unittest.mock import patch
from models import MetadataServer
from deserializer import DeserializationError


def serialize_metadata_server(
    ip_address: str,
    port: int,
    version: str,
) -> bytearray:
    """
    Serializes MetadataServer data into a bytearray buffer for testing.
    Mirrors the MetadataServer.from_buffer logic.
    """
    buffer = bytearray()

    version_parts = [int(p) for p in version.split('.')]

    buffer.extend(struct.pack(">LHHBB", int(ipaddress.ip_address(ip_address)), port,
                              version_parts[0], version_parts[1],
                              version_parts[2]))

    return buffer


def serialize_metadata_server_status(
    status: int,
    metadata_version: int,
) -> bytearray:
    """
    Serializes MetadataServer data into a bytearray buffer for testing.
    Mirrors the MetadataServer.from_buffer logic.
    """
    buffer = bytearray()
    buffer.extend(struct.pack(">LBQ", 1, status, metadata_version))

    return buffer


class TestMetadataServerDeserialization(unittest.TestCase):

    @patch('socket.gethostbyaddr', return_value=('mocked-hostname', [], []))
    def test_from_buffer(self, mock_gethostbyaddr):
        version = "1.0.0"
        ip_address = "10.0.0.1"
        port = 9000
        # personality = ""
        # state = ""
        # metadata_version = 10

        mock_buffer = serialize_metadata_server(ip_address, port, version)
        buffer_copy = bytearray(mock_buffer)

        server = MetadataServer.from_buffer(buffer_copy)

        self.assertEqual(server.id, 0)  # ID is set by caller
        self.assertEqual(server.hostname, "mocked-hostname")
        self.assertEqual(server.ip_address, ip_address)
        self.assertEqual(server.port, port)
        self.assertEqual(server.version, version)
        self.assertEqual(len(buffer_copy), 0)

    def test_from_buffer_deserialization_error(self):
        # Buffer too short for basic fields
        short_buffer = bytearray(struct.pack(">L",
                                             int(ipaddress.ip_address("192.168.50.1"))))  # Just ip_address
        with self.assertRaises(DeserializationError):
            MetadataServer.from_buffer(short_buffer)

    def test_from_buffer_unresolved(self):
        version = "1.0.0"
        ip_address = "255.255.255.255"
        port = 9000
        mock_buffer = serialize_metadata_server(ip_address, port, version)

        server = MetadataServer.from_buffer(mock_buffer)
        self.assertEqual(server.hostname, "(unresolved)")

    @patch('socket.gethostbyaddr', side_effect=lambda ip: ('mocked-hostname-' + ip, [], []))
    def test_get_list(self, mock_gethostbyaddr):
        server1_data = {
            "version": "1.0.0", "ip_address": "10.0.0.1",
            "port": 9000
        }
        server2_data = {
            "version": "1.0.1", "ip_address": "10.0.0.1",
            "port": 9001
        }

        mock_server1_buffer = serialize_metadata_server(**server1_data)
        mock_server2_buffer = serialize_metadata_server(**server2_data)

        list_buffer = bytearray()
        # Master version is first before vector.
        # Apparently it's only use is a hack on saunafs-admin to sort the
        # master, so we can put whatever we want here really.
        list_buffer.extend(struct.pack(">L",
                                       12345))
        list_buffer.extend(struct.pack(">L", 2))  # length of vector
        list_buffer.extend(mock_server1_buffer)
        list_buffer.extend(mock_server2_buffer)

        servers = MetadataServer.get_list(list_buffer)

        self.assertEqual(len(servers), 2)

        # Assertions for server 1
        # MetadataServer.get_list does not include master and starts counting from 2
        self.assertEqual(servers[0].id, 2)
        self.assertEqual(servers[0].hostname, f"mocked-hostname-{server1_data['ip_address']}")
        self.assertEqual(servers[0].ip_address, server1_data['ip_address'])
        self.assertEqual(servers[0].port, server1_data['port'])
        self.assertEqual(servers[0].version, server1_data['version'])

        # Assertions for server 2
        self.assertEqual(servers[1].id, 3)
        self.assertEqual(servers[1].hostname, f"mocked-hostname-{server2_data['ip_address']}")
        self.assertEqual(servers[1].ip_address, server2_data['ip_address'])
        self.assertEqual(servers[1].port, server2_data['port'])
        self.assertEqual(servers[1].version, server2_data['version'])

        self.assertEqual(len(list_buffer), 0)

    def test_from_buffer_status(self):
        version = "1.0.0"
        ip_address = "10.0.0.1"
        port = 9000
        # personality = ""
        # state = ""
        # metadata_version = 10

        server_mock_buffer = serialize_metadata_server(ip_address, port, version)
        server = MetadataServer.from_buffer(server_mock_buffer)

        server_status = serialize_metadata_server_status(1, 500)
        server.status_from_buffer(server_status)
        self.assertEqual(server.state, "running")
        self.assertEqual(server.personality, "master")
        self.assertEqual(server.metadata_version, 500)

        server_status = serialize_metadata_server_status(2, 500)
        server.status_from_buffer(server_status)
        self.assertEqual(server.state, "connected")
        self.assertEqual(server.personality, "shadow")

        server_status = serialize_metadata_server_status(3, 500)
        server.status_from_buffer(server_status)
        self.assertEqual(server.state, "disconnected")
        self.assertEqual(server.personality, "shadow")

        server_status = serialize_metadata_server_status(4, 500)
        server.status_from_buffer(server_status)
        self.assertEqual(server.state, "(unknown: code 4)")
        self.assertEqual(server.personality, "(unknown: code 4)")
