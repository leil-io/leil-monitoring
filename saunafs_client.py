import socket
import struct
import select
import logging
from typing import List, Tuple
from models import (Mount,
                    Export,
                    MetadataServer,
                    FsCheckInfo,
                    ChunkOperationsInfo,
                    ChunkMatrix,
                    Metalogger,
                    Server,
                    Disk,
                    SystemInfo
                    )
from deserializer import unpack_string


# Message type and protocol constants
PROTO_BASE = 0

CLTOMA_INFO = (PROTO_BASE + 510)
MATOCL_INFO = (PROTO_BASE + 511)
INFO = (CLTOMA_INFO, MATOCL_INFO)

CLTOMA_FSTEST_INFO = (PROTO_BASE + 512)
MATOCL_FSTEST_INFO = (PROTO_BASE + 513)
FSTEST_INFO = (CLTOMA_FSTEST_INFO, MATOCL_FSTEST_INFO)

CLTOMA_CHUNKS_MATRIX = (PROTO_BASE + 516)
MATOCL_CHUNKS_MATRIX = (PROTO_BASE + 517)
CHUNKS_MATRIX = (CLTOMA_CHUNKS_MATRIX, MATOCL_CHUNKS_MATRIX)

CLTOMA_CHUNKSTEST_INFO = (PROTO_BASE + 514)
MATOCL_CHUNKSTEST_INFO = (PROTO_BASE + 515)
CHUNKSTEST_INFO = (CLTOMA_CHUNKSTEST_INFO, MATOCL_CHUNKSTEST_INFO)

CLTOMA_CSERV_LIST = (PROTO_BASE + 500)
MATOCL_CSERV_LIST = (PROTO_BASE + 501)
CSERV_LIST = (CLTOMA_CSERV_LIST, MATOCL_CSERV_LIST)

SAU_CLTOMA_CSERV_LIST = 1549
SAU_MATOCL_CSERV_LIST = 1550
SAU_CSERV_LIST = (SAU_CLTOMA_CSERV_LIST, SAU_MATOCL_CSERV_LIST)

SAU_CLTOMA_METADATASERVERS_LIST = 1522
SAU_MATOCL_METADATASERVERS_LIST = 1523
METADATASERVERS_LIST = (SAU_CLTOMA_METADATASERVERS_LIST, SAU_MATOCL_METADATASERVERS_LIST)

SAU_CLTOMA_METADATASERVER_STATUS = 1545
SAU_MATOCL_METADATASERVER_STATUS = 1546
METADATASERVER_STATUS = (SAU_CLTOMA_METADATASERVER_STATUS, SAU_MATOCL_METADATASERVER_STATUS)

CLTOCS_HDD_LIST_V2 = (PROTO_BASE + 600)
MATOCL_HDD_LIST_V2 = (PROTO_BASE + 601)
CS_HDD_LIST = (CLTOCS_HDD_LIST_V2, MATOCL_HDD_LIST_V2)

CLTOMA_MLOG_LIST = (PROTO_BASE + 522)
MATOCL_MLOG_LIST = (PROTO_BASE + 523)
MLOG_LIST = (CLTOMA_MLOG_LIST, MATOCL_MLOG_LIST)

CUTOAN_CHART = (PROTO_BASE + 504)
ANTOCU_CHART = (PROTO_BASE + 505)
CHART = (CUTOAN_CHART, ANTOCU_CHART)

SAU_CLTOMA_MOUNT_INFO_LIST = 1609
SAU_MATOCL_MOUNT_INFO_LIST = 1610
MOUNT_INFO_LIST = (SAU_CLTOMA_MOUNT_INFO_LIST, SAU_MATOCL_MOUNT_INFO_LIST)

CLTOMA_SESSION_LIST = (PROTO_BASE + 508)
MATOCL_SESSION_LIST = (PROTO_BASE + 509)
SESSION_LIST = (CLTOMA_SESSION_LIST, MATOCL_SESSION_LIST)

CLTOMA_EXPORTS_INFO = (PROTO_BASE + 520)
MATOCL_EXPORTS_INFO = (PROTO_BASE + 521)
EXPORTS_INFO = (CLTOMA_EXPORTS_INFO, MATOCL_EXPORTS_INFO)


class SaunaFSClient:
    def __init__(self, master_host: str, master_port: int):
        self.master_host = master_host
        self.master_port = master_port
        self.master_version = self._get_master_version()

    def _my_send(self, sock: socket.socket, msg: bytes):
        totalsent = 0
        logging.debug(f"Sending message: {msg}")
        while totalsent < len(msg):
            sent = sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("Socket connection broken")
            totalsent += sent

    def _my_recv(self, sock: socket.socket, length: int) -> bytes:
        msg = b''
        logging.debug(f"Receiving message with length {length}")
        while len(msg) < length:
            ready = select.select([sock], [], [], 5)
            if not ready[0]:
                raise RuntimeError("Socket connection timed out")
            chunk = sock.recv(length - len(msg))
            if not chunk:
                raise RuntimeError("Socket connection broken")
            msg += chunk
        return msg

    def send_and_receive(self, msg: Tuple[int, int], payload: bytes = b'', version: int = 0, host: str = "", port: str = "") -> bytearray:
        if not host:
            host = self.master_host
        if not port:
            port = self.master_port

        cmd, expected = msg
        isV2 = cmd > 1000

        if isV2:
            length = 4 + len(payload)
            request = struct.pack(">LLL", cmd, length, version) + payload
            logging.debug(f"Sending V2 request: cmd={cmd}, length={length}, version={version}, payload={payload}")
        else:
            length = len(payload)
            request = struct.pack(">LL", cmd, length) + payload
            logging.debug(f"Sending V1 request: cmd={cmd}, length={length}, payload={payload}")

        with socket.socket() as s:
            s.settimeout(5)
            logging.debug(f"Connecting to {host}:{port}")
            s.connect((host, port))

            self._my_send(s, request)
            header = self._my_recv(s, 8)

            respCmd, respLength = struct.unpack(">LL", header)
            logging.debug(f"Header received: cmd={respCmd}, length={respLength}")

            if respCmd != expected:
                raise RuntimeError(f"Received wrong response command: {respCmd}, expected {expected}")

            respPayload = self._my_recv(s, respLength)
            if isV2:
                if len(respPayload) < 4:
                    raise ValueError("V2 response payload is too short for version field")
                respVersion = struct.unpack(">L", respPayload[:4])[0]
                logging.debug(f"V2 response version: {respVersion}")
                return bytearray(respPayload[4:])
            else:
                return bytearray(respPayload)

    def _deserialize_string(self, buffer: bytearray, legacy: bool = False) -> str:
        return unpack_string(buffer, legacy)

    def _get_master_version(self) -> Tuple[int, int, int]:
        try:
            data = self.send_and_receive(INFO)
            if len(data) >= 4:
                v1, v2, v3 = struct.unpack(">HBB", data[:4])
                return (v1, v2, v3)
            return (0, 0, 0)
        except Exception:
            return (0, 0, 0)

    def get_info(self) -> SystemInfo:
        buffer = self.send_and_receive(INFO)
        return SystemInfo.from_buffer(buffer)

    def get_chart(self, host: str, port: int, chart_id: int) -> bytes:
        payload = struct.pack(">L", chart_id)
        return self.send_and_receive(CHART, payload, host=host, port=port)

    def get_servers(self) -> List[Server]:
        payload = b'\x00'  # Dummy, must be included
        buffer = self.send_and_receive(
            SAU_CSERV_LIST,
            payload,
            version=0
        )
        return Server.get_list(buffer)

    def get_disks(self) -> List[Disk]:
        allDisks = []
        for server in self.get_servers():
            if server.is_disconnected:
                continue
            buffer = self.send_and_receive(
                CS_HDD_LIST,
                host=server.ip_address,
                port=server.port,
            )
            serverDisks = Disk.get_list(buffer)
            for disk in serverDisks:
                disk.path = f"{server.hostname}:{disk.path}"
            allDisks.extend(serverDisks)
        return allDisks

    def get_metaloggers(self) -> List[Metalogger]:
        buffer = self.send_and_receive(MLOG_LIST)
        return Metalogger.get_list(buffer)

    def get_mounts(self) -> List[Mount]:
        extra_mount_info_buffer = self.send_and_receive(MOUNT_INFO_LIST)
        # Send vmode=1 to request extended information
        payload = struct.pack(">B", 1)
        buffer = self.send_and_receive(SESSION_LIST, payload)
        return Mount.get_list(buffer, extra_mount_info_buffer)

    def get_exports(self) -> List[Export]:
        data = self.send_and_receive(EXPORTS_INFO)
        return Export.get_list(data)

    def get_fs_check_info(self) -> FsCheckInfo:
        data = self.send_and_receive(FSTEST_INFO)
        return FsCheckInfo.from_buffer(data)

    def get_chunk_operations_info(self) -> ChunkOperationsInfo:
        buffer = self.send_and_receive(CHUNKSTEST_INFO)
        return ChunkOperationsInfo.from_buffer(buffer)

    def get_chunk_matrix(self) -> ChunkMatrix:
        payload = struct.pack(">B", 0)
        buffer = self.send_and_receive(CHUNKS_MATRIX, payload)

        matrix = []
        for _ in range(11):
            row = list(struct.unpack(">LLLLLLLLLLL", buffer[:44]))
            matrix.append(row)
            del buffer[:44]

        return ChunkMatrix(matrix=matrix)

    def get_metadata_servers(self) -> List[MetadataServer]:
        servers = []

        # Add the master server
        master_ip = socket.gethostbyname(self.master_host)
        master_v1, master_v2, master_v3 = self.master_version
        master_personality, master_state, master_metadata_version = self.get_metadata_server_status(self.master_host, self.master_port)

        servers.append(MetadataServer(
            id=1,
            hostname=self.master_host,
            ip_address=master_ip,
            port=self.master_port,
            version=f"{master_v1}.{master_v2}.{master_v3}",
            personality=master_personality,
            state=master_state,
            metadata_version=master_metadata_version
        ))

        # Get shadow servers
        buffer = self.send_and_receive(
            METADATASERVERS_LIST,
            b""
        )
        servers = MetadataServer.get_list(buffer)

        for i, server in enumerate(servers):
            payload = struct.pack(">L", 0)
            buffer = self.send_and_receive(
                METADATASERVER_STATUS,
                payload
            )
            server.status_from_buffer(buffer)

        return servers
