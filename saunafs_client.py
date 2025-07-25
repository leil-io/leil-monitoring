import socket
import struct
import select
import logging
from typing import List, Tuple, Dict
from models import (SystemInfo,
                    Server,
                    Disk,
                    Metalogger,
                    Mount,
                    Export,
                    MetadataServer,
                    FsCheckInfo,
                    ChunkOperationsInfo,
                    OperationStats,
                    ChunkMatrix)
from deserializer import unpack_list, unpack_string


# Protocol constants
PROTO_BASE = 0
CLTOMA_INFO = (PROTO_BASE + 510)
MATOCL_INFO = (PROTO_BASE + 511)
CLTOMA_CSERV_LIST = (PROTO_BASE + 500)
MATOCL_CSERV_LIST = (PROTO_BASE + 501)
CLTOCS_HDD_LIST_V2 = (PROTO_BASE + 600)
MATOCL_HDD_LIST_V2 = (PROTO_BASE + 601)
CLTOMA_MLOG_LIST = (PROTO_BASE + 522)
MATOCL_MLOG_LIST = (PROTO_BASE + 523)
CLTOMA_SESSION_LIST = (PROTO_BASE + 508)
MATOCL_SESSION_LIST = (PROTO_BASE + 509)
CLTOMA_EXPORTS_INFO = (PROTO_BASE + 520)
MATOCL_EXPORTS_INFO = (PROTO_BASE + 521)
CLTOMA_FSTEST_INFO = (PROTO_BASE + 512)
MATOCL_FSTEST_INFO = (PROTO_BASE + 513)
CLTOMA_CHUNKSTEST_INFO = (PROTO_BASE + 514)
MATOCL_CHUNKSTEST_INFO = (PROTO_BASE + 515)
CLTOMA_CHUNKS_MATRIX = (PROTO_BASE + 516)
MATOCL_CHUNKS_MATRIX = (PROTO_BASE + 517)


CUTOAN_CHART = (PROTO_BASE + 504)
ANTOCU_CHART = (PROTO_BASE + 505)

SAU_CLTOMA_CSERV_LIST = 1549
SAU_MATOCL_CSERV_LIST = 1550
SAU_CLTOMA_METADATASERVERS_LIST = 1522
SAU_MATOCL_METADATASERVERS_LIST = 1523
SAU_CLTOMA_METADATASERVER_STATUS = 1545
SAU_MATOCL_METADATASERVER_STATUS = 1546
SAU_CLTOMA_HOSTNAME = 1551
SAU_MATOCL_HOSTNAME = 1552
SAU_CLTOMA_MOUNT_INFO_LIST = 1609
SAU_MATOCL_MOUNT_INFO_LIST = 1610


# Message type constants
INFO = (CLTOMA_INFO, MATOCL_INFO)
CSERV_LIST = (CLTOMA_CSERV_LIST, MATOCL_CSERV_LIST)
SAU_CSERV_LIST = (SAU_CLTOMA_CSERV_LIST, SAU_MATOCL_CSERV_LIST)
CS_HDD_LIST = (CLTOCS_HDD_LIST_V2, MATOCL_HDD_LIST_V2)
MLOG_LIST = (CLTOMA_MLOG_LIST, MATOCL_MLOG_LIST)
CHART = (CUTOAN_CHART, ANTOCU_CHART)
EXPORTS_INFO = (CLTOMA_EXPORTS_INFO, MATOCL_EXPORTS_INFO)
MOUNT_INFO_LIST = (SAU_CLTOMA_MOUNT_INFO_LIST, SAU_MATOCL_MOUNT_INFO_LIST)
SESSION_LIST = (CLTOMA_SESSION_LIST, MATOCL_SESSION_LIST)


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

    def get_chart(self, host: str, port: int, chart_id: int) -> bytes:
        payload = struct.pack(">L", chart_id)
        return self.send_and_receive(CHART, payload, host=host, port=port)

    def _get_mounts_info(self) -> Dict[int, str]:
        mounts_info = {}
        try:
            buffer = self.send_and_receive(MOUNT_INFO_LIST)
            vector_size, = struct.unpack(">L", buffer[:4])
            del buffer[:4]
            for _ in range(vector_size):
                session_id, = struct.unpack(">L", buffer[:4])
                del buffer[:4]
                mount_info = self._deserialize_string(buffer)
                mounts_info[session_id] = mount_info
        except Exception as e:
            logging.warning(f"Could not get extra mount info: {e}")
        return mounts_info

    def get_mounts(self) -> List[Mount]:
        extra_mount_info = Mount.get_mounts_info()
        # Send vmode=1 to request extended information
        payload = struct.pack(">B", 1)
        buffer = self.send_and_receive(SESSION_LIST, payload)
        return Mount.get_list(buffer, extra_mount_info)

    def get_exports(self) -> List[Export]:
        allExports = []
        data = self.send_and_receive(EXPORTS_INFO)
        buffer = bytearray(data)

        i = 1
        while len(buffer) >= 12:
            fip1, fip2, fip3, fip4, tip1, tip2, tip3, tip4, pleng = struct.unpack(">BBBBBBBBL", buffer[:12])
            del buffer[:12]

            path = buffer[:pleng].decode('utf-8', errors='replace')
            del buffer[:pleng]

            # This part of the protocol seems to have many versions.
            # This is a simplified parser for a common version.
            if len(buffer) >= 22:
                v1, v2, v3, exportflags, sesflags, rootuid, rootgid, mapalluid, mapallgid = struct.unpack(">HBBBBLLLL", buffer[:22])
                del buffer[:22]
            else:
                break

            ip_from = f"{fip1}.{fip2}.{fip3}.{fip4}"
            ip_to = f"{tip1}.{tip2}.{tip3}.{tip4}"

            flags = []
            if sesflags & 1:
                flags.append("ro")
            else:
                flags.append("rw")
            if sesflags & 2:
                flags.append("dynamic_ip")
            if sesflags & 4:
                flags.append("ignore_gid")
            if sesflags & 8:
                flags.append("quota_admin")
            if sesflags & 16:
                flags.append("map_all")

            allExports.append(Export(
                id=i,
                ip_from=ip_from,
                ip_to=ip_to,
                path=path,
                flags=", ".join(flags)
            ))
            i += 1
        return allExports

    def get_fs_check_info(self) -> FsCheckInfo:
        data = self.send_and_receive((CLTOMA_FSTEST_INFO, MATOCL_FSTEST_INFO))
        buffer = bytearray(data)
        loop_start, loop_end, files, ug_files, m_files, chunks, ug_chunks, m_chunks, msg_buff_leng = struct.unpack(">LLLLLLLLL", buffer[:36])
        del buffer[:36]
        message = buffer.decode('utf-8', errors='replace')

        return FsCheckInfo(
            loop_start=loop_start,
            loop_end=loop_end,
            files=files,
            under_goal_files=ug_files,
            missing_files=m_files,
            chunks=chunks,
            under_goal_chunks=ug_chunks,
            missing_chunks=m_chunks,
            message=message
        )

    def get_chunk_operations_info(self) -> ChunkOperationsInfo:
        buffer = self.send_and_receive((CLTOMA_CHUNKSTEST_INFO, MATOCL_CHUNKSTEST_INFO))
        loop_start, loop_end, del_invalid, n_del_invalid, del_unused, n_del_unused, del_dclean, n_del_dclean, del_ogoal, n_del_ogoal, rep_ugoal, n_rep_ugoal, rebalance = struct.unpack(">LLLLLLLLLLLLL", buffer[:52])

        return ChunkOperationsInfo(
            loop_start=loop_start,
            loop_end=loop_end,
            delete_invalid=del_invalid,
            not_delete_invalid=n_del_invalid,
            delete_unused=del_unused,
            not_delete_unused=n_del_unused,
            delete_disk_clean=del_dclean,
            not_delete_disk_clean=n_del_dclean,
            delete_over_goal=del_ogoal,
            not_delete_over_goal=n_del_ogoal,
            replicate_under_goal=rep_ugoal,
            not_replicate_under_goal=n_rep_ugoal,
            rebalance=rebalance
        )

    def get_chunk_matrix(self) -> ChunkMatrix:
        payload = struct.pack(">B", 0)
        buffer = self.send_and_receive((CLTOMA_CHUNKS_MATRIX, MATOCL_CHUNKS_MATRIX), payload)

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
            (SAU_CLTOMA_METADATASERVERS_LIST, SAU_MATOCL_METADATASERVERS_LIST),
            b""
        )
        master_version, = struct.unpack(">L", buffer[:4])
        del buffer[:4]
        vector_size, = struct.unpack(">L", buffer[:4])
        del buffer[:4]
        logging.debug(f"get_metadata_servers vector_size: {vector_size}")

        for i in range(vector_size):
            ip, port, v1, v2, v3 = struct.unpack(">LHHBB", buffer[:10])
            del buffer[:10]
            ip_str = socket.inet_ntoa(struct.pack(">L", ip))
            try:
                hostname = socket.gethostbyaddr(ip_str)[0]
            except socket.herror:
                hostname = "(unresolved)"

            personality, state, metadata_version = self.get_metadata_server_status(ip_str, port)

            servers.append(MetadataServer(
                id=i + 2,
                hostname=hostname,
                ip_address=ip_str,
                port=port,
                version=f"{v1}.{v2}.{v3}",
                personality=personality,
                state=state,
                metadata_version=metadata_version
            ))

        return servers

    def get_metadata_server_status(self, host: str, port: int) -> Tuple[str, str, int]:
        payload = struct.pack(">L", 0)
        buffer = self.send_and_receive(
            (SAU_CLTOMA_METADATASERVER_STATUS, SAU_MATOCL_METADATASERVER_STATUS),
            payload
        )
        _, status, metadata_version = struct.unpack(">LBQ", buffer)

        if status == 1:
            return ("master", "running", metadata_version)
        elif status == 2:
            return ("shadow", "connected", metadata_version)
        elif status == 3:
            return ("shadow", "disconnected", metadata_version)
        else:
            return ("(unknown)", "(unknown)", metadata_version)

    def get_operation_stats_from_list(self, list: List[int]) -> OperationStats:
        stats = OperationStats(
            statfs=list[0],
            getattr=list[1],
            setattr=list[2],
            lookup=list[3],
            mkdir=list[4],
            rmdir=list[5],
            symlink=list[6],
            readlink=list[7],
            mknod=list[8],
            unlink=list[9],
            rename=list[10],
            link=list[11],
            readdir=list[12],
            open=list[13],
            read=list[14],
            write=list[15],
            total=sum(list)
        )
        return stats
