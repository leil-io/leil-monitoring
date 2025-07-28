from __future__ import annotations
from pydantic import BaseModel
from typing import List, Optional, Dict
from deserializer import unpack_list, unpack_primitive, unpack_string, DeserializationError, unpack_from
import logging
import socket
import struct


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
    def get_list(buffer: bytearray) -> List[Server]:
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


class Disk(BaseModel):
    path: str
    status: str
    last_error: str
    total_space: int
    used_space: int
    chunks: int

    @staticmethod
    def get_list(buffer) -> List[Disk]:
        disks = []
        while len(buffer) > 0:
            disks.append(Disk.from_buffer(buffer))
        return disks

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


class Metalogger(BaseModel):
    id: int
    hostname: str
    ip_address: str
    version: str

    @staticmethod
    def get_list(buffer: bytearray) -> List[Metalogger]:
        allLoggers = []
        while len(buffer) > 0:
            allLoggers.append(Metalogger.from_buffer(buffer))
            allLoggers[-1].id = len(allLoggers)
        return allLoggers

    @classmethod
    def from_buffer(cls, buffer: bytearray) -> Metalogger:
        try:
            v1, v2, v3, ip1, ip2, ip3, ip4 = unpack_from("HBBBBBB", buffer)
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
    def get_from_list(list: List[int]) -> OperationStats:
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
    root_path: str
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

    @staticmethod
    def get_mounts_info(buffer: bytearray) -> Dict[int, str]:
        mounts_info = {}
        try:
            vector_size, = struct.unpack(">L", buffer[:4])
            del buffer[:4]
            for _ in range(vector_size):
                session_id, = struct.unpack(">L", buffer[:4])
                del buffer[:4]
                mount_info = unpack_string(buffer)
                mounts_info[session_id] = mount_info
        except Exception as e:
            logging.warning(f"Could not get extra mount info: {e}")
            return {}
        return mounts_info

    @staticmethod
    def get_list(buffer: bytearray, extra_mount_info_buffer: bytearray) -> List[Mount]:
        extra_mount_info = Mount.get_mounts_info(extra_mount_info_buffer)
        allMounts = []
        statsCount, = struct.unpack(">H", buffer[:2])
        del buffer[:2]

        while len(buffer) > 0:
            mount = Mount.from_buffer(buffer, statsCount)
            mount.id = len(allMounts) + 1
            if mount.session_id in extra_mount_info:
                mount.mount_info = "\n" + extra_mount_info[mount.session_id]

            allMounts.append(mount)
        return allMounts

    @classmethod
    def from_buffer(cls, buffer: bytearray, stats_count: int) -> Mount:
        try:
            session_id, ip1, ip2, ip3, ip4, v1, v2, v3 = unpack_from("LBBBBHBB", buffer)

            root_path = unpack_string(buffer, legacy=True)
            mounted_path = unpack_string(buffer, legacy=True)

            sesflags, rootuid, rootgid, mapalluid, mapallgid = unpack_from("BLLLL", buffer)

            # The vmode we sent means these fields should be present
            mingoal, maxgoal, mintrashtime, maxtrashtime = unpack_from("BBLL", buffer)

            current_op_stats_list = []
            for _ in range(stats_count):
                stat, = unpack_from("L", buffer)
                current_op_stats_list.append(stat)

            current_op_stats = OperationStats.get_from_list(current_op_stats_list)

            last_hour_op_stats_list = []
            for _ in range(stats_count):
                stat, = unpack_from("L", buffer)
                last_hour_op_stats_list.append(stat)

            last_hour_op_stats = OperationStats.get_from_list(current_op_stats_list)

            ip_address = f"{ip1}.{ip2}.{ip3}.{ip4}"
            try:
                hostname = socket.gethostbyaddr(ip_address)[0]
            except socket.herror:
                hostname = "(unresolved)"

            flags = []
            if sesflags & 1:
                flags.append("ro")
            if sesflags & 2:
                flags.append("dynamic_ip")
            if sesflags & 4:
                flags.append("ignore_gid")
            if sesflags & 8:
                flags.append("quota_admin")
            if sesflags & 16:
                flags.append("map_all")

            flags = ", ".join(flags)

            return cls(
                id=0,  # Caller sets this
                session_id=session_id,
                hostname=hostname,
                ip_address=ip_address,
                mounted_path=mounted_path,
                version=f"{v1}.{v2}.{v3}",
                root_path=root_path,
                mount_info="",  # Caller sets this
                flags=flags,
                root_uid=rootuid,
                root_gid=rootgid,
                map_all_uid=mapalluid,
                map_all_gid=mapallgid,
                min_goal=mingoal,
                max_goal=maxgoal,
                min_trash_time=mintrashtime,
                max_trash_time=maxtrashtime,
                current_op_stats=current_op_stats,
                last_hour_op_stats=last_hour_op_stats,
            )
        except DeserializationError as e:
            raise DeserializationError(f"Failed to deserialize Mount: {e}")


class Export(BaseModel):
    id: int
    ip_from: str
    ip_to: str
    path: str
    flags: str

    @staticmethod
    def get_list(buffer: bytearray) -> List[Export]:
        allExports = []
        i = 1
        while len(buffer) >= 12:
            export = Export.from_buffer(buffer)
            export.id = i
            allExports.append(export)
            i += 1
        return allExports

    @classmethod
    def from_buffer(cls, buffer: bytearray) -> Export:
        try:
            fip1, fip2, fip3, fip4, tip1, tip2, tip3, tip4 = unpack_from("BBBBBBBB", buffer)

            path = unpack_string(buffer, True)

            # This part of the protocol seems to have many versions.
            # This is a simplified parser for a common version.
            if len(buffer) >= 22:
                v1, v2, v3, exportflags, sesflags, rootuid, rootgid, mapalluid, mapallgid = unpack_from("HBBBBLLLL", buffer)
            else:
                raise DeserializationError("Unsupported master version")

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

            return cls(
                id=0,  # Set by caller
                ip_from=ip_from,
                ip_to=ip_to,
                path=path,
                flags=", ".join(flags)
            )
        except DeserializationError as e:
            raise DeserializationError(f"Failed to deserialize Export: {e}")


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

    @classmethod
    def from_buffer(cls, buffer: bytearray) -> FsCheckInfo:
        try:
            loop_start, loop_end, files, ug_files, m_files, chunks, ug_chunks, m_chunks = unpack_from("LLLLLLLL", buffer)
            message = unpack_string(buffer, True)
            return cls(
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
        except DeserializationError as e:
            raise DeserializationError(f"Failed to deserialize FsCheckInfo: {e}")


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
