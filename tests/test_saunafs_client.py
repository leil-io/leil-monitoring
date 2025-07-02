import socket
import struct
from unittest.mock import MagicMock, patch

import pytest

from saunafs_client import (
    SaunaFSClient, MATOCL_INFO, ANTOCU_CHART, SAU_MATOCL_CSERV_LIST,
    MATOCL_HDD_LIST_V2, MATOCL_MLOG_LIST
)

from models import SystemInfo

versionPayload = struct.pack(">HBB", 2, 5, 1)


@pytest.fixture
def mockSocket():
    """A pytest fixture that mocks the socket object and its methods."""
    with patch('socket.socket') as mock_socket_class, \
            patch('select.select') as mock_select:
        mock_sock_instance = MagicMock()
        mock_socket_class.return_value.__enter__.return_value = mock_sock_instance

        # Make select.select return the socket, indicating it's ready to read
        mock_select.return_value = ([mock_sock_instance], [], [])

        # Configure send to return the length of the data
        mock_sock_instance.send.side_effect = lambda data: len(data)
        yield mock_sock_instance


def test_get_master_version_success(mockSocket):
    """
    Tests that the client correctly fetches and parses the master version
    during initialization.
    """

    # The _get_master_version call in __init__ will receive this
    mockSocket.recv.side_effect = [
        struct.pack(">LL", MATOCL_INFO, len(versionPayload)),
        versionPayload,
    ]

    client = SaunaFSClient(master_host="testhost", master_port=9421)

    assert client.master_version == (2, 5, 1)
    mockSocket.connect.assert_called_once_with(("testhost", 9421))


def test_get_master_version_connection_error(mockSocket):
    """
    Tests that a connection error during version check is handled gracefully.
    """
    mockSocket.connect.side_effect = socket.error("Connection refused")

    # The exception is caught internally and a default version is returned
    client = SaunaFSClient(master_host="testhost", master_port=9421)
    assert client.master_version == (0, 0, 0)


def test_get_system_info_success(mockSocket):
    """
    Tests the successful retrieval and parsing of system information.
    """
    system_info_payload = struct.pack(
        ">HBBQQQQLQLLLLLLLL",
        2, 5, 1, 536870912, 10995116277760, 5497558138880, 1073741824,
        100, 2147483648, 50, 5000, 1000, 4000, 500, 20000, 40000, 38000
    )

    # The client makes two separate connections/calls.
    # The first is in __init__ for the version, the second is in get_system_info.
    mockSocket.recv.side_effect = [
        # Response for _get_master_version in __init__
        struct.pack(">LL", MATOCL_INFO, len(versionPayload)),
        versionPayload,
        # Response for get_system_info
        struct.pack(">LL", MATOCL_INFO, len(system_info_payload)),
        system_info_payload
    ]

    client = SaunaFSClient(master_host="testhost", master_port=9421)
    system_info = client.get_system_info()

    assert isinstance(system_info, SystemInfo)
    assert client.master_version == (2, 5, 1)  # Ensure version is still correct
    assert system_info.version == "2.5.1"
    assert system_info.ram_used == 536870912
    assert system_info.total_space == 10995116277760
    assert system_info.chunks == 20000


def test_get_system_info_wrong_response(mockSocket):
    """
    Tests that the client handles an unexpected response command.
    """
    wrong_command = 9999

    mockSocket.recv.side_effect = [
        # Valid response for version check
        struct.pack(">LL", MATOCL_INFO, len(versionPayload)),
        versionPayload,
        # Invalid response for get_system_info
        struct.pack(">LL", wrong_command, 0),
        b''
    ]

    client = SaunaFSClient(master_host="testhost", master_port=9421)

    with pytest.raises(RuntimeError,
                       match=f"Received wrong response command: {wrong_command}, expected {MATOCL_INFO}"):
        client.get_system_info()


def test_get_chart_success(mockSocket):
    """
    Tests the successful retrieval of chart data.
    """
    chart_payload = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'

    mockSocket.recv.side_effect = [
        # Response for _get_master_version in __init__
        struct.pack(">LL", MATOCL_INFO, len(versionPayload)),
        versionPayload,
        # Response for get_chart
        struct.pack(">LL", ANTOCU_CHART, len(chart_payload)),
        chart_payload
    ]

    client = SaunaFSClient(master_host="testhost", master_port=9421)
    chart_data = client.get_chart("chart_host", 9000, 1)

    assert chart_data == chart_payload
    # The first call is to the master, the second to the chart host
    assert mockSocket.connect.call_count == 2
    mockSocket.connect.assert_called_with(("chart_host", 9000))


def test_get_servers_success(mockSocket):
    """
    Tests the successful retrieval and parsing of a list of chunk servers.
    """

    server1_label = "server-one" + "\x00"
    server1_payload = struct.pack(
        ">BBBBBBBBHQQLQQLLL",
        0, 2, 5, 1, 192, 168, 1, 10, 9422, 500, 1000, 50, 10, 20, 1, 0, len(server1_label)
    ) + server1_label.encode('utf-8')

    server2_label = "server-two" + "\x00"
    server2_payload = struct.pack(
        ">BBBBBBBBHQQLQQLLL",
        1, 2, 5, 0, 192, 168, 1, 11, 9422, 800, 1000, 80, 0, 0, 0, 5, len(server2_label)
    ) + server2_label.encode('utf-8')

    serversPayload = struct.pack(">L", 2) + server1_payload + server2_payload

    # V2 response includes a version field (which _send_and_receive strips)
    v2RespHeader = struct.pack(">L", 0)  # version 0
    full_payload = v2RespHeader + serversPayload

    mockSocket.recv.side_effect = [
        # Response for _get_master_version
        struct.pack(">LL", MATOCL_INFO, len(versionPayload)),
        versionPayload,
        # Response for get_servers
        struct.pack(">LL", SAU_MATOCL_CSERV_LIST, len(full_payload)),
        full_payload
    ]

    # Mock the reverse DNS lookup
    with patch('socket.gethostbyaddr') as mock_gethostbyaddr:
        mock_gethostbyaddr.side_effect = [
            ("host-one.local", [], []),
            ("host-two.local", [], [])
        ]

        client = SaunaFSClient(master_host="testhost", master_port=9421)
        servers = client.get_servers()

    assert len(servers) == 2

    assert servers[0].id == 1
    assert servers[0].hostname == "host-one.local"
    assert servers[0].ip_address == "192.168.1.10"
    assert not servers[0].is_disconnected
    assert servers[0].label == "server-one"
    assert servers[0].total_space == 1000
    assert servers[0].chunks_tobedeleted == 1

    assert servers[1].id == 2
    assert servers[1].hostname == "host-two.local"
    assert servers[1].ip_address == "192.168.1.11"
    assert servers[1].is_disconnected == True
    assert servers[1].label == "server-two"
    assert servers[1].used_space == 800
    assert servers[1].error_count == 5


def test_get_disks_success(mockSocket):
    """
    Tests the successful retrieval and parsing of a list of disks.
    """

    serverLabel = "server-one" + "\x00"
    serverPayload = struct.pack(
        ">BBBBBBBBHQQLQQLLL",
        0, 2, 5, 1, 192, 168, 1, 10, 9422, 500, 1000, 50, 10, 20, 1, 0, len(serverLabel)
    ) + serverLabel.encode('utf-8')
    serversPayload = struct.pack(">L", 1) + serverPayload
    v2RespHeader = struct.pack(">L", 0)  # version 0
    fullServersPayload = v2RespHeader + serversPayload

    disk_path = b"/mnt/disk1"
    disk_payload = struct.pack(
        ">BQLQQL",
        0,     # flags: 8-bit unsigned
        0,     # errchunkid: 64-bit unsigned
        0,     # errtime: 32-bit
        2000,  # used: 64-bit unsigned
        4000,  # total: 64-bit unsinged
        200,   # chunkscount: 64-bit unsigned
    )
    entryPayload = struct.pack(">HB", len(disk_payload) + len(disk_path) + 1, len(disk_path)) + disk_path + disk_payload

    mockSocket.recv.side_effect = [
        struct.pack(">LL", MATOCL_INFO, len(versionPayload)),
        versionPayload,
        struct.pack(">LL", SAU_MATOCL_CSERV_LIST, len(fullServersPayload)),
        fullServersPayload,
        struct.pack(">LL", MATOCL_HDD_LIST_V2, len(entryPayload)),
        entryPayload
    ]

    with patch('socket.gethostbyaddr') as mock_gethostbyaddr:
        mock_gethostbyaddr.return_value = ("host-one.local", [], [])

        client = SaunaFSClient(master_host="testhost", master_port=9421)
        disks = client.get_disks()

    print(disks)
    assert len(disks) == 1
    disk = disks[0]
    assert disk.path == "host-one.local:/mnt/disk1"
    assert disk.status == "ok"
    assert disk.total_space == 4000
    assert disk.used_space == 2000
    assert disk.chunks == 200


def test_get_metaloggers_success(mockSocket):
    """
    Tests the successful retrieval and parsing of a list of metaloggers.
    """

    logger1_v1 = 5  # Interesting the first version number is 16-bit?
    logger1_v2 = 0
    logger1_v3 = 0
    logger1_ip1 = 192
    logger1_ip2 = 168
    logger1_ip3 = 50
    logger1_ip4 = 201

    logger2_v1 = 4
    logger2_v2 = 9
    logger2_v3 = 1

    logger2_ip1 = 192
    logger2_ip2 = 168
    logger2_ip3 = 50
    logger2_ip4 = 204

    metalogger1_payload = struct.pack(
        ">HBBBBBB",
        logger1_v1,
        logger1_v2,
        logger1_v3,
        logger1_ip1,
        logger1_ip2,
        logger1_ip3,
        logger1_ip4
    )

    metalogger2_payload = struct.pack(
        ">HBBBBBB",
        logger2_v1,
        logger2_v2,
        logger2_v3,
        logger2_ip1,
        logger2_ip2,
        logger2_ip3,
        logger2_ip4
    )

    payload = metalogger1_payload + metalogger2_payload

    mockSocket.recv.side_effect = [
        struct.pack(">LL", MATOCL_INFO, len(versionPayload)),
        versionPayload,
        struct.pack(">LL", MATOCL_MLOG_LIST, len(payload)),
        payload
    ]
    with patch('socket.gethostbyaddr') as mock_gethostbyaddr:
        def side_effect(ip) -> str:
            if ip == "192.168.50.201":
                return ("metalogger_01", [], [])
            elif ip == "192.168.50.204":
                return ("metalogger_02", [], [])

        mock_gethostbyaddr.side_effect = side_effect

        client = SaunaFSClient(master_host="testhost", master_port=9421)
        metaloggers = client.get_metaloggers()

    assert len(metaloggers) == 2
    metalogger1 = metaloggers[0]
    assert metalogger1.ip_address == "192.168.50.201"
    assert metalogger1.version == "5.0.0"
    assert metalogger1.hostname == "metalogger_01"
    assert metalogger1.id == 1

    metalogger2 = metaloggers[1]
    assert metalogger2.ip_address == "192.168.50.204"
    assert metalogger2.version == "4.9.1"
    assert metalogger2.hostname == "metalogger_02"
    assert metalogger2.id == 2
