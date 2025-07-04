from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional
from deserializer import unpack_list, unpack_primitive, DeserializationError
import socket
import struct
import saunafs_client

PROTO_BASE = 0

CLTOMA_INFO = (PROTO_BASE + 510)
MATOCL_INFO = (PROTO_BASE + 511)
INFO = (CLTOMA_INFO, MATOCL_INFO)

class SystemInfo(BaseModel):
    version: str
    ram_used: int
    total_space: int
    avail_space: int
    trash_space: int
    trash_files: int
    reserved_space: int
    reserved_files: int
    total_objects: int
    directories: int
    files: int
    symlinks: int
    chunks: int
    all_copies: int
    regular_copies: int

    @staticmethod
    def get(client: saunafs_client.SaunaFSClient) -> SystemInfo():
        buffer = client.send_and_receive(INFO)
        return SystemInfo.from_buffer(buffer)

    @classmethod
    def from_buffer(cls, buffer: bytearray) -> SystemInfo:
        try:
            v1, v2, v3, mem, total, avail, trspace, trfiles, respace, refiles, nodes, dirs, files, symlinks, chunks, allcopies, tdcopies = unpack_primitive(
                "HBBQQQQLQLLLLLLLL", buffer
            )
            return cls(
                version=f"{v1}.{v2}.{v3}", ram_used=mem, total_space=total, avail_space=avail,
                trash_space=trspace, trash_files=trfiles, reserved_space=respace, reserved_files=refiles,
                total_objects=nodes, directories=dirs, files=files, symlinks=symlinks, chunks=chunks,
                all_copies=allcopies, regular_copies=tdcopies,
            )
        except Exception as e:
            raise DeserializationError(f"Failed to deserialize SystemInfo: {e}")


SAU_CLTOMA_CSERV_LIST = 1549
SAU_MATOCL_CSERV_LIST = 1550
SAU_CSERV_LIST = (SAU_CLTOMA_CSERV_LIST, SAU_MATOCL_CSERV_LIST)


class Server(BaseModel):
    id: int
    hostname: str
    ip_address: str
    port: int
    version: str
    is_disconnected: bool
    label: str
    used_space: int
    total_space: int
    chunks: int
    used_space_tobedeleted: int
    total_space_tobedeleted: int
    chunks_tobedeleted: int
    error_count: int

    @staticmethod
    def get_list(client: saunafs_client.SaunaFSClient) -> List[Server]:
        payload = b'\x00'  # Dummy, must be included
        buffer = client.send_and_receive(
            SAU_CSERV_LIST,
            payload,
            version=0
        )
        servers = unpack_list(buffer, Server)
        for i, server in enumerate(servers):
            server.id = i + 1
        print(servers)
        return servers

    @classmethod
    def from_buffer(cls, buffer: bytearray) -> Server:
        try:
            # Unpack the main server data structure
            disconnected, v1, v2, v3, ip1, ip2, ip3, ip4, port, used, total, chunks, tdused, tdtotal, tdchunks, errcnt, label_length = unpack_primitive(
                "BBBBBBBBHQQLQQLLL", buffer
            )

            # Unpack the label string
            if len(buffer) < label_length:
                raise DeserializationError(f"Buffer too short for server label. Need {label_length}, have {len(buffer)}.")
            label = buffer[:label_length - 1].decode('utf-8', errors='replace')
            del buffer[:label_length]

            ip_address = f"{ip1}.{ip2}.{ip3}.{ip4}"
            try:
                hostname = socket.gethostbyaddr(ip_address)[0]
            except (socket.herror, socket.gaierror):
                hostname = "(unresolved)"

            return cls(
                id=0,  # ID will be assigned by the caller
                hostname=hostname,
                ip_address=ip_address,
                port=port,
                version=f"{v1}.{v2}.{v3}",
                is_disconnected=bool(disconnected),
                label=label,
                used_space=used,
                total_space=total,
                chunks=chunks,
                used_space_tobedeleted=tdused,
                total_space_tobedeleted=tdtotal,
                chunks_tobedeleted=tdchunks,
                error_count=errcnt
            )
        except Exception as e:
            raise DeserializationError(f"Failed to deserialize Server: {e}")


CLTOCS_HDD_LIST_V2 = (PROTO_BASE + 600)
MATOCL_HDD_LIST_V2 = (PROTO_BASE + 601)
CS_HDD_LIST = (CLTOCS_HDD_LIST_V2, MATOCL_HDD_LIST_V2)


class Disk(BaseModel):
    path: str
    status: str
    last_error: str
    total_space: int
    used_space: int
    chunks: int

    @staticmethod
    def get_list(client: saunafs_client.SaunaFSClient) -> List[Disk]:
        allDisks = []
        for server in Server.get_list(client):
            if server.is_disconnected:
                continue
            buffer = client.send_and_receive(
                CS_HDD_LIST,
                host=server.ip_address,
                port=server.port,
            )
            disks = Disk.from_buffer_list(buffer)
            for disk in disks:
                disk.path = f"{server.hostname}:{disk.path}"
            allDisks.extend(disks)
        return allDisks

    @classmethod
    def from_buffer(cls, buffer: bytearray) -> Disk:
        try:
            entry_size, = unpack_primitive("H", buffer[:2])
            del buffer[:2]
            if len(buffer) < entry_size:
                raise DeserializationError(f"Buffer too short for disk entry. Need {entry_size}, have {len(buffer)}.")

            entry_buffer = bytearray(buffer[:entry_size])
            del buffer[:entry_size]

            path_len = entry_buffer[0]
            del entry_buffer[0]
            path = entry_buffer[:path_len].decode('utf-8')
            del entry_buffer[:path_len]

            flags, err_chunk_id, err_time, used, total, chunks_cnt, = unpack_primitive(
                "BQLQQL", entry_buffer
            )

            status = "ok"
            if flags == 1:
                status = 'marked for removal'
            elif flags == 2:
                status = 'damaged'
            elif flags == 3:
                status = 'damaged, marked for removal'

            last_error = "no errors"
            if err_time > 0:
                last_error = f"{err_time} on chunk: {err_chunk_id}"

            return cls(
                path=path,
                status=status,
                last_error=last_error,
                total_space=total,
                used_space=used,
                chunks=chunks_cnt
            )
        except Exception as e:
            raise DeserializationError(f"Failed to deserialize Disk: {e}")

    @classmethod
    def from_buffer_list(cls, buffer: bytearray) -> List[Disk]:
        allDisks = []
        while len(buffer) > 0:
            disk = Disk.from_buffer(buffer)
            allDisks.append(disk)
        return allDisks


CLTOMA_MLOG_LIST = (PROTO_BASE + 522)
MATOCL_MLOG_LIST = (PROTO_BASE + 523)
MLOG_LIST = (CLTOMA_MLOG_LIST, MATOCL_MLOG_LIST)


class Metalogger(BaseModel):
    id: int
    hostname: str
    ip_address: str
    version: str

    @staticmethod
    def get_list(client: saunafs_client.SaunaFSClient) -> List[Metalogger]:
        allLoggers = []
        buffer = client.send_and_receive(MLOG_LIST)
        while len(buffer) > 0:
            allLoggers.append(Metalogger.from_buffer(buffer))
            allLoggers[-1].id = len(allLoggers)
        return allLoggers

    @classmethod
    def from_buffer(cls, buffer: bytearray) -> Metalogger:

        try:
            v1, v2, v3, ip1, ip2, ip3, ip4 = struct.unpack(">HBBBBBB", buffer[:8])
            del buffer[:8]
            ip_address = f"{ip1}.{ip2}.{ip3}.{ip4}"
            version = f"{v1}.{v2}.{v3}"
            try:
                hostname = socket.gethostbyaddr(ip_address)[0]
            except socket.herror:
                hostname = "(unresolved)"

            return cls(
                id=0,  # Caller sets this
                hostname=hostname,
                ip_address=ip_address,
                version=version,
            )
        except DeserializationError as e:
            raise DeserializationError(f"Failed to deserialize Metalogger: {e}")


class OperationStats(BaseModel):
    statfs: int
    getattr: int
    setattr: int
    lookup: int
    mkdir: int
    rmdir: int
    symlink: int
    readlink: int
    mknod: int
    unlink: int
    rename: int
    link: int
    readdir: int
    open: int
    read: int
    write: int
    total: int

    @staticmethod
    def get_from_list(self, list: List[int]) -> OperationStats:
        return OperationStats(
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


class Mount(BaseModel):
    id: int
    session_id: int
    hostname: str
    ip_address: str
    mounted_path: str
    version: str
    mount_info: str
    flags: str
    root_uid: int
    root_gid: int
    map_all_uid: int
    map_all_gid: int
    min_goal: Optional[int] = None
    max_goal: Optional[int] = None
    min_trash_time: Optional[int] = None
    max_trash_time: Optional[int] = None
    current_op_stats: Optional[OperationStats] = None
    last_hour_op_stats: Optional[OperationStats] = None


class Export(BaseModel):
    id: int
    ip_from: str
    ip_to: str
    path: str
    flags: str


class MetadataServer(BaseModel):
    id: int
    hostname: str
    ip_address: str
    port: int
    version: str
    personality: str
    state: str
    metadata_version: int


class FsCheckInfo(BaseModel):
    loop_start: int
    loop_end: int
    files: int
    under_goal_files: int
    missing_files: int
    chunks: int
    under_goal_chunks: int
    missing_chunks: int
    message: str


class ChunkOperationsInfo(BaseModel):
    loop_start: int
    loop_end: int
    delete_invalid: int
    not_delete_invalid: int
    delete_unused: int
    not_delete_unused: int
    delete_disk_clean: int
    not_delete_disk_clean: int
    delete_over_goal: int
    not_delete_over_goal: int
    replicate_under_goal: int
    not_replicate_under_goal: int
    rebalance: int


class ChunkMatrix(BaseModel):
    matrix: List[List[int]]
