"""
This file is part of leil-monitoring.
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

from __future__ import annotations
from pydantic import BaseModel
from typing import List, Optional, Dict
from .deserializer import unpack_list, unpack_primitive, unpack_string, DeserializationError, unpack_from
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


class DiskStats(BaseModel):
    read_bytes: int
    read_bytes_persecond: float
    read_ops: int
    read_usec: int
    read_usec_avg: float
    read_usec_max: int
    read_block_size_avg: float

    written_bytes: int
    written_bytes_persecond: float
    write_ops: int
    written_usec: int
    written_usec_avg: float
    written_usec_max: int
    written_block_size_avg: float

    fsync_ops: int
    fsync_usec: int
    fsync_usec_avg: float
    fsync_usec_max: int

    # TODO(Urmas): Write a test for this
    @classmethod
    def from_buffer(cls, buffer: bytearray) -> Disk:
        try:
            rbytes, wbytes, usecreadsum, usecwritesum, usecfsyncsum, = unpack_primitive("QQQQQ", buffer)
            rops, wops, fsyncops, usecreadmax, usecwritemax, usecfsyncmax, = unpack_primitive("LLLLLL", buffer)

            if usecreadsum > 0:
                bytes_read_persecond = rbytes * 1_000_000 / usecreadsum
            else:
                bytes_read_persecond = 0
            if usecwritesum + usecfsyncsum > 0:
                bytes_written_persecond = wbytes * 1_000_000 / (usecwritesum + usecfsyncsum)
            else:
                bytes_written_persecond = 0

            if rops > 0:
                read_usec_avg = usecreadsum / rops
                read_block_size = rbytes / rops
            else:
                read_usec_avg = 0
                read_block_size = 0
            if wops > 0:
                written_usec_avg = usecwritesum / wops
                write_block_size = wbytes / wops
            else:
                written_usec_avg = 0
                write_block_size = 0

            if fsyncops > 0:
                fsync_usec_avg = usecfsyncsum / fsyncops
            else:
                fsync_usec_avg = 0

            return cls(
                read_bytes=rbytes,
                read_bytes_persecond=bytes_read_persecond,
                read_ops=rops,
                read_usec=usecreadsum,
                read_usec_avg=read_usec_avg,
                read_usec_max=usecreadmax,
                read_block_size_avg=read_block_size,
                written_bytes=wbytes,
                written_bytes_persecond=bytes_written_persecond,
                write_ops=wops,
                written_usec=usecwritesum,
                written_usec_avg=written_usec_avg,
                written_usec_max=usecwritemax,
                written_block_size_avg=write_block_size,
                fsync_ops=fsyncops,
                fsync_usec=usecfsyncsum,
                fsync_usec_avg=fsync_usec_avg,
                fsync_usec_max=usecfsyncmax,
            )
        except Exception as e:
            raise DeserializationError(f"Failed to deserialize DiskStats: {e}")


class Disk(BaseModel):
    path: str
    status: str
    last_error: str
    total_space: int
    used_space: int
    chunks: int
    minute_stats: DiskStats
    hour_stats: DiskStats
    day_stats: DiskStats

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

            DEFAULT_STATUS = "OK"
            status = DEFAULT_STATUS
            if flags & 0x1:
                status = 'Marked for removal'
            elif flags & 0x2:
                status = 'Damaged'
            elif flags & 0x3:
                status = 'Damaged, marked for removal'
            elif flags & 0x6 or flags & 0x4:
                status = "Scanning"
            elif flags & 0x7 or flags & 0x5:
                status = "Scanning, marked for removal"

            last_error = "No errors"
            if err_time > 0:
                last_error = f"{err_time} on chunk: {err_chunk_id}"
                if status == DEFAULT_STATUS:
                    status = "Errors reported"
            elif flags & 0x2:
                last_error = "Read/Write error"

            # TODO(Urmas): Update SFSCommunication.h because it's completely wrong
            # Most importantly, there are 60-bit offsets to these for minute, hour and days
            minute_stats = DiskStats.from_buffer(entry_buffer)
            hour_stats = DiskStats.from_buffer(entry_buffer)
            day_stats = DiskStats.from_buffer(entry_buffer)

            return cls(
                path=path,
                status=status,
                last_error=last_error,
                total_space=total,
                used_space=used,
                chunks=chunks_cnt,
                minute_stats=minute_stats,
                hour_stats=hour_stats,
                day_stats=day_stats,
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

class INotifier(BaseModel):
    id: int
    hostname: str
    ip_address: str
    version: str

    @staticmethod
    def get_list(buffer: bytearray) -> List[INotifier]:
        all_inotifiers = []
        count, = unpack_from("L", buffer)
        while count > 0:
            all_inotifiers.append(INotifier.from_buffer(buffer))
            all_inotifiers[-1].id = len(all_inotifiers)
            count -= 1
        return all_inotifiers

    @classmethod
    def from_buffer(cls, buffer: bytearray) -> INotifier:
        try:
            ip1, ip2, ip3, ip4, v1, v2, v3 = unpack_from("BBBBHBB", buffer)
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
            raise DeserializationError(f"Failed to deserialize INotifier: {e}")

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

            last_hour_op_stats = OperationStats.get_from_list(last_hour_op_stats_list)

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

    @classmethod
    def get_list(cls, buffer: bytearray) -> List[MetadataServer]:
        servers = []
        master_version, = struct.unpack(">L", buffer[:4])
        del buffer[:4]
        vector_size, = struct.unpack(">L", buffer[:4])
        del buffer[:4]
        logging.debug(f"MetadataServer::get_list: vector_size: {vector_size}")
        for i in range(vector_size):
            server = MetadataServer.from_buffer(buffer)
            server.id = i + 2  # master not included here
            servers.append(server)

        return servers

    @classmethod
    def from_buffer(cls, buffer: bytearray) -> MetadataServer:
        try:
            ip, port, v1, v2, v3 = unpack_from("LHHBB", buffer)
            ip_str = socket.inet_ntoa(struct.pack(">L", ip))

            return cls(
                id=0,  # Set by caller
                hostname="",  # Set by caller
                ip_address=ip_str,
                port=port,
                version=f"{v1}.{v2}.{v3}",
                personality="",  # Set by status_from_buffer
                state="",  # Set by status_from_buffer
                metadata_version=-1  # Set by status_from_buffer

            )
        except DeserializationError as e:
            raise DeserializationError(f"Failed to deserialize MetadataServer: {e}")

    def status_from_buffer(self, buffer: bytearray):
        _, status, self.metadata_version = struct.unpack(">LBQ", buffer)  # First is msgid (useless)
        logging.debug(f"server {self.hostname} status: {status}")
        if status == 1:
            self.personality = "master"
            self.state = "running"
        elif status == 2:
            self.personality = "shadow"
            self.state = "connected"
        elif status == 3:
            self.personality = "shadow"
            self.state = "disconnected"
        else:
            self.personality = f"(unknown: code {status})"
            self.state = f"(unknown: code {status})"


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

    @classmethod
    def from_buffer(cls, buffer: bytearray) -> ChunkOperationsInfo:
        try:
            loop_start, loop_end, del_invalid, n_del_invalid, del_unused, n_del_unused, del_dclean, n_del_dclean, del_ogoal, n_del_ogoal, rep_ugoal, n_rep_ugoal, rebalance = struct.unpack(">LLLLLLLLLLLLL", buffer[:52])

            return cls(
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
        except DeserializationError as e:
            raise DeserializationError(f"Failed to deserialize ChunkOperationsInfo: {e}")


class Goal(BaseModel):
    id: int
    name: str
    definition: str

    @staticmethod
    def get_list(buffer: bytearray) -> List[Goal]:
        try:
            goals = []
            vector_size, = unpack_from("L", buffer)
            for i in range(vector_size):
                goal = Goal.from_buffer(buffer)
                goals.append(goal)

            return goals

        except DeserializationError as e:
            raise DeserializationError(f"Failed to deserialize Goal: {e}")

    @classmethod
    def from_buffer(cls, buffer: bytearray) -> Goal:
        try:
            id, = unpack_from("H", buffer)
            name = unpack_string(buffer)
            definition = unpack_string(buffer)
            return cls(
                id=id,
                name=name,
                definition=definition,
            )
        except DeserializationError as e:
            raise DeserializationError(f"Failed to deserialize Goal: {e}")


class ChunkHealth(BaseModel):
    regular_only: bool
    safe: Dict[int, int]
    endangered: Dict[int, int]
    lost: Dict[int, int]
    # Up to eleven values usually
    replication: Dict[int, List[int]]
    deletion: Dict[int, List[int]]

    @classmethod
    def from_buffer(cls, buffer: bytearray) -> ChunkHealth:
        try:
            regular_only, = unpack_from("B", buffer)

            # --- helper to read dicts (key: uint8, value: uint64) ---
            def read_simple_dict():
                result = {}
                count, = unpack_from("L", buffer)
                for _ in range(count):
                    goal_id, = unpack_from("B", buffer)
                    value, = unpack_from("Q", buffer)
                    result[goal_id] = value
                return result

            # --- helper to read dicts (key: uint8, value: 11 × uint64) ---
            def read_complex_dict():
                result = {}
                count, = unpack_from("L", buffer)
                for _ in range(count):
                    goal_id, = unpack_from("B", buffer)
                    values = list(unpack_from("11Q", buffer))
                    result[goal_id] = values
                return result

            safe = read_simple_dict()
            endangered = read_simple_dict()
            lost = read_simple_dict()
            replication = read_complex_dict()
            deletion = read_complex_dict()

            return cls(
                regular_only=regular_only,
                safe=safe,
                endangered=endangered,
                lost=lost,
                replication=replication,
                deletion=deletion
            )

        except DeserializationError as e:
            raise DeserializationError(f"Failed to deserialize ChunkOperationsInfo: {e}")


class ChunkMatrix(BaseModel):
    matrix: List[List[int]]


class ChunkMappedHealth(BaseModel):
    name: str
    total: int
    safe: int
    endangered: int
    lost: int
    # Up to eleven values usually
    replication: List[int]
    deletion: List[int]

    @classmethod
    def from_chunk_health(cls, health: ChunkHealth, goals: List[Goal]) -> List[ChunkMappedHealth]:
        mapped_goals = []
        for idx, goal in enumerate(goals):
            safe = health.safe.get(goal.id, 0)
            endangered = health.endangered.get(goal.id, 0)
            lost = health.lost.get(goal.id, 0)
            replication = health.replication.get(goal.id, [])
            deletion = health.deletion.get(goal.id, [])
            mapped_goals.append(
                cls(
                    name=goal.name,
                    safe=safe,
                    endangered=endangered,
                    lost=lost,
                    replication=replication,
                    deletion=deletion,
                    total=safe + endangered + lost
                )
            )
        return mapped_goals
