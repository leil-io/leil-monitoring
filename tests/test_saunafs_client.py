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

import socket
import struct
from unittest.mock import MagicMock, patch

import pytest

from saunafs_client.saunafs_client import (
    SaunaFSClient, MATOCL_INFO, ANTOCU_CHART, SAU_MATOCL_CSERV_LIST,
    MATOCL_HDD_LIST_V2
)

from saunafs_client.models import (
    SystemInfo
)


versionPayload = struct.pack(">HBB", 2, 5, 1)


def _mock_initial_version_response():
    """Helper to return the initial master version response side effect."""
    return [
        struct.pack(">LL", MATOCL_INFO, len(versionPayload)),
        versionPayload,
    ]


def _create_server_payload(
    disconnected, v1, v2, v3, ip1, ip2, ip3, ip4, port, used, total, chunks,
    tdused, tdtotal, tdchunks, errcnt, label
):
    """Helper to create a single server payload."""
    server_label_encoded = (label + "\x00").encode('utf-8')
    return struct.pack(
        ">BBBBBBBBHQQLQQLLL",
        disconnected, v1, v2, v3, ip1, ip2, ip3, ip4, port, used, total, chunks,
        tdused, tdtotal, tdchunks, errcnt, len(server_label_encoded)
    ) + server_label_encoded


def _create_disk_payload(
    flags, err_chunk_id, err_time, used, total, chunks_cnt, disk_path
):
    """Helper to create a single disk payload.
    Pads stats for each period with 0's
    """
    disk_payload_data = struct.pack(
        ">BQLQQL",
        flags, err_chunk_id, err_time, used, total, chunks_cnt,
    )
    for _ in range(0, 3):
        disk_payload_data += struct.pack(">QQQQQLLLLLL",
                                         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,)
    return struct.pack(
        ">HB", len(disk_payload_data) + len(disk_path) + 1, len(disk_path)
    ) + disk_path + disk_payload_data


def _create_metalogger_payload(v1, v2, v3, ip1, ip2, ip3, ip4):
    """Helper to create a single metalogger payload."""
    return struct.pack(
        ">HBBBBBB",
        v1, v2, v3, ip1, ip2, ip3, ip4
    )


def _mock_gethostbyaddr(mock_gethostbyaddr, ip_to_hostname_map):
    """Helper to mock socket.gethostbyaddr with a dictionary of mappings."""
    def side_effect(ip):
        if ip in ip_to_hostname_map:
            return (ip_to_hostname_map[ip], [], [])
        raise socket.herror(1, "Host not found")
    mock_gethostbyaddr.side_effect = side_effect


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

    mockSocket.recv.side_effect = _mock_initial_version_response()


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
    mockSocket.recv.side_effect = _mock_initial_version_response() + [
        # Response for get_system_info
        struct.pack(">LL", MATOCL_INFO, len(system_info_payload)),
        system_info_payload
    ]

    client = SaunaFSClient(master_host="testhost", master_port=9421)
    system_info = client.get_info()

    assert isinstance(system_info, SystemInfo)
    assert client.master_version == (2, 5, 1)
    assert system_info.version == "2.5.1"
    assert system_info.ram_used == 536870912
    assert system_info.total_space == 10995116277760
    assert system_info.chunks == 20000


def test_get_system_info_wrong_response(mockSocket):
    """
    Tests that the client handles an unexpected response command.
    """
    wrong_command = 9999

    mockSocket.recv.side_effect = _mock_initial_version_response() + [
        # Invalid response for get_system_info
        struct.pack(">LL", wrong_command, 0),
        b''
    ]

    client = SaunaFSClient(master_host="testhost", master_port=9421)

    with pytest.raises(RuntimeError,
                       match=f"Received wrong response command: {wrong_command}, expected {MATOCL_INFO}"):
        client.get_info()


def test_get_chart_success(mockSocket):
    """
    Tests the successful retrieval of chart data.
    """
    chart_payload = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'

    mockSocket.recv.side_effect = _mock_initial_version_response() + [
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

    server1_payload = _create_server_payload(
        disconnected=0, v1=2, v2=5, v3=1, ip1=192, ip2=168, ip3=1, ip4=10, port=9422,
        used=500, total=1000, chunks=50, tdused=10, tdtotal=20, tdchunks=1, errcnt=0,
        label="server-one"
    )

    server2_payload = _create_server_payload(
        disconnected=1, v1=2, v2=5, v3=0, ip1=192, ip2=168, ip3=1, ip4=11, port=9422,
        used=800, total=1000, chunks=80, tdused=0, tdtotal=0, tdchunks=0, errcnt=5,
        label="server-two"
    )

    serversPayload = struct.pack(">L", 2) + server1_payload + server2_payload

    # V2 response includes a version field (which _send_and_receive strips)
    v2RespHeader = struct.pack(">L", 0)  # version 0
    full_payload = v2RespHeader + serversPayload

    mockSocket.recv.side_effect = _mock_initial_version_response() + [
        # Response for get_servers
        struct.pack(">LL", SAU_MATOCL_CSERV_LIST, len(full_payload)),
        full_payload
    ]

    # Mock the reverse DNS lookup
    with patch('socket.gethostbyaddr') as mock_gethostbyaddr:
        _mock_gethostbyaddr(mock_gethostbyaddr, {
            "192.168.1.10": "host-one.local",
            "192.168.1.11": "host-two.local"
        })

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
    assert servers[1].is_disconnected is True
    assert servers[1].label == "server-two"
    assert servers[1].used_space == 800
    assert servers[1].error_count == 5


def test_get_disks_success(mockSocket):
    """
    Tests the successful retrieval and parsing of a list of disks.
    """

    serverPayload = _create_server_payload(
        disconnected=0, v1=2, v2=5, v3=1, ip1=192, ip2=168, ip3=1, ip4=10, port=9422,
        used=500, total=1000, chunks=50, tdused=10, tdtotal=20, tdchunks=1, errcnt=0,
        label="server-one"
    )
    serversPayload = struct.pack(">L", 1) + serverPayload
    v2RespHeader = struct.pack(">L", 0)  # version 0
    fullServersPayload = v2RespHeader + serversPayload

    disk_path_bytes = b"/mnt/disk1"
    entryPayload = _create_disk_payload(
        flags=0, err_chunk_id=0, err_time=0, used=2000, total=4000, chunks_cnt=200,
        disk_path=disk_path_bytes
    )

    mockSocket.recv.side_effect = _mock_initial_version_response() + [
        struct.pack(">LL", SAU_MATOCL_CSERV_LIST, len(fullServersPayload)),
        fullServersPayload,
        struct.pack(">LL", MATOCL_HDD_LIST_V2, len(entryPayload)),
        entryPayload
    ]

    with patch('socket.gethostbyaddr') as mock_gethostbyaddr:
        _mock_gethostbyaddr(mock_gethostbyaddr, {"192.168.1.10": "host-one.local"})

        client = SaunaFSClient(master_host="testhost", master_port=9421)
        disks = client.get_disks()

    print(disks)
    assert len(disks) == 1
    disk = disks[0]
    assert disk.path == "host-one.local:/mnt/disk1"
    assert disk.status.lower() == "ok"
    assert disk.total_space == 4000
    assert disk.used_space == 2000
    assert disk.chunks == 200
