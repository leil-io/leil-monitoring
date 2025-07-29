import struct
from typing import List
import ipaddress


def serialize_string(s: str, legacy: bool = False) -> bytes:
    """
    Serializes a string into bytes, mirroring the unpack_string logic.
    - V2 strings are null-terminated and prefixed with their length (including null).
    - Legacy strings are not null-terminated and are prefixed with their length.
    """
    s_bytes = s.encode('utf-8')
    if legacy:
        length = len(s_bytes)
        return struct.pack(">L", length) + s_bytes
    else:
        length = len(s_bytes) + 1  # +1 for null terminator
        return struct.pack(">L", length) + s_bytes + b'\x00'


def serialize_version(version: str) -> List[int]:
    return [int(p) for p in version.split('.')]


def serialize_mount(
    session_id: int,
    ip_address: str,
    version: str,
    root_path: str,
    mounted_path: str,
    sesflags: int,
    root_uid: int,
    root_gid: int,
    map_all_uid: int,
    map_all_gid: int,
    min_goal: int,
    max_goal: int,
    min_trash_time: int,
    max_trash_time: int,
    current_op_stats_list: List[int],
    last_hour_op_stats_list: List[int]
) -> bytearray:
    """
    Serializes Mount data into a bytearray buffer for testing.
    """
    buffer = bytearray()

    ip_parts = [int(p) for p in ip_address.split('.')]
    v_parts = [int(p) for p in version.split('.')]
    buffer.extend(struct.pack(">LBBBBHBB", session_id, ip_parts[0], ip_parts[1], ip_parts[2], ip_parts[3], v_parts[0], v_parts[1], v_parts[2]))

    buffer.extend(serialize_string(root_path, legacy=True))

    buffer.extend(serialize_string(mounted_path, legacy=True))

    buffer.extend(struct.pack(">BLLLL", sesflags, root_uid, root_gid, map_all_uid, map_all_gid))

    buffer.extend(struct.pack(">BBLL", min_goal, max_goal, min_trash_time, max_trash_time))

    for stat in current_op_stats_list:
        buffer.extend(struct.pack(">L", stat))

    for stat in last_hour_op_stats_list:
        buffer.extend(struct.pack(">L", stat))

    return buffer


def serialize_info(
    version: str,
    ram_used: int,
    total_space: int,
    avail_space: int,
    trash_space: int,
    trash_files: int,
    reserved_space: int,
    reserved_files: int,
    total_objects: int,
    directories: int,
    files: int,
    symlinks: int,
    chunks: int,
    all_copies: int,
    regular_copies: int,
) -> bytes:
    """
    Serializes mount info for get_mounts_info.
    """
    buffer = bytearray()
    version_parts = [int(p) for p in version.split('.')]

    buffer.extend(struct.pack(
        ">HBBQQQQLQLLLLLLLL",
        version_parts[0],
        version_parts[1],
        version_parts[2],
        ram_used,
        total_space,
        avail_space,
        trash_space,
        trash_files,
        reserved_space,
        reserved_files,
        total_objects,
        directories,
        files,
        symlinks,
        chunks,
        all_copies,
        regular_copies,
    ))
    return buffer


def serialize_mount_info(session_id: int, mount_info: str) -> bytes:
    """
    Serializes mount info for get_mounts_info.
    """
    buffer = bytearray()
    buffer.extend(struct.pack(">L", session_id))
    buffer.extend(serialize_string(mount_info, legacy=False))  # Mount info is V2 string
    return buffer


def serialize_metalogger(
    version: str,
    ip_address: str
) -> bytearray:
    """
    Serializes Metalogger data into a bytearray buffer for testing.
    """
    buffer = bytearray()
    v_parts = [int(p) for p in version.split('.')]
    ip_parts = [int(p) for p in ip_address.split('.')]
    # HBBBBBB (v1, v2, v3, ip1, ip2, ip3, ip4)
    buffer.extend(struct.pack(">HBBBBBB", v_parts[0], v_parts[1], v_parts[2], ip_parts[0], ip_parts[1], ip_parts[2], ip_parts[3]))
    return buffer


def serialize_server(
    is_disconnected: bool,
    version: str,
    ip_address: str,
    port: int,
    used_space: int,
    total_space: int,
    chunks: int,
    used_space_tobedeleted: int,
    total_space_tobedeleted: int,
    chunks_tobedeleted: int,
    error_count: int,
    label: str
) -> bytearray:
    """
    Serializes Server data into a bytearray buffer for testing.
    Mirrors the Server.from_buffer logic.
    """
    buffer = bytearray()

    version_parts = [int(p) for p in version.split('.')]
    ip_parts = [int(p) for p in ip_address.split('.')]
    disconnected_byte = 1 if is_disconnected else 0

    buffer.extend(struct.pack(">BBBBBBBBHQQLQQLL",
                              disconnected_byte,
                              version_parts[0], version_parts[1], version_parts[2],
                              ip_parts[0], ip_parts[1], ip_parts[2], ip_parts[3],
                              port,
                              used_space, total_space, chunks,
                              used_space_tobedeleted, total_space_tobedeleted, chunks_tobedeleted,
                              error_count))

    buffer.extend(serialize_string(label))

    return buffer


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


def serialize_export(
    ip_from: str,
    ip_to: str,
    path: str,
    version: str,
    exportflags: int,
    sesflags: int,
    root_uid: int,
    root_gid: int,
    map_all_uid: int,
    map_all_gid: int
) -> bytearray:
    """
    Serializes Export data into a bytearray buffer for testing.
    Mirrors the Export.from_buffer logic.
    """
    buffer = bytearray()

    ip_from_parts = [int(p) for p in ip_from.split('.')]
    ip_to_parts = [int(p) for p in ip_to.split('.')]
    version_parts = [int(p) for p in version.split('.')]

    # fip1, fip2, fip3, fip4, tip1, tip2, tip3, tip4, pleng
    buffer.extend(struct.pack(">BBBBBBBB",
                              ip_from_parts[0], ip_from_parts[1], ip_from_parts[2], ip_from_parts[3],
                              ip_to_parts[0], ip_to_parts[1], ip_to_parts[2], ip_to_parts[3],
                              ))
    buffer.extend(serialize_string(path, True))
    # v1, v2, v3, exportflags, sesflags, rootuid, rootgid, mapalluid, mapallgid
    buffer.extend(struct.pack(">HBBBBLLLL",
                              version_parts[0], version_parts[1], version_parts[2],
                              exportflags, sesflags, root_uid, root_gid, map_all_uid, map_all_gid))
    return buffer


def serialize_disk(
    path: str,
    flags: int,
    err_chunk_id: int,
    err_time: int,
    used_space: int,
    total_space: int,
    chunks_cnt: int
) -> bytearray:
    """
    Serializes Disk data into a bytearray buffer for testing.
    Mirrors the Disk.from_buffer logic.
    """
    buffer = bytearray()

    path_bytes = path.encode('utf-8')
    path_len = len(path_bytes)

    inner_entry = struct.pack(">BQLQQL",
                              flags,
                              err_chunk_id,
                              err_time,
                              used_space,
                              total_space,
                              chunks_cnt)

    entry_size = 1 + path_len + len(inner_entry)

    buffer.extend(struct.pack(">H", entry_size))
    buffer.extend(struct.pack(">B", path_len))
    buffer.extend(path_bytes)
    buffer.extend(inner_entry)

    return buffer


def serialize_fscheck_info(
    loop_start: int,
    loop_end: int,
    files: int,
    under_goal_files: int,
    missing_files: int,
    chunks: int,
    under_goal_chunks: int,
    missing_chunks: int,
    message: str
) -> bytes:
    """
    Serializes FsCheckInfo data into a bytearray buffer for testing.
    Mirrors the get_fs_check_info logic in saunafs_client.py.
    """
    buffer = bytearray()

    buffer.extend(struct.pack(
        ">LLLLLLLL",
        loop_start,
        loop_end,
        files,
        under_goal_files,
        missing_files,
        chunks,
        under_goal_chunks,
        missing_chunks,
    ))
    buffer.extend(serialize_string(message, True))
    return buffer
