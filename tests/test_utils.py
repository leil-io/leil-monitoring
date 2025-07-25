import struct
from typing import List

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
        length = len(s_bytes) + 1 # +1 for null terminator
        return struct.pack(">L", length) + s_bytes + b'\x00'

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

    # LBBBBHBB (session_id, ip1-4, v1-3)
    ip_parts = [int(p) for p in ip_address.split('.')]
    v_parts = [int(p) for p in version.split('.')]
    buffer.extend(struct.pack(">LBBBBHBB", session_id, ip_parts[0], ip_parts[1], ip_parts[2], ip_parts[3], v_parts[0], v_parts[1], v_parts[2]))

    # root_path (legacy string)
    buffer.extend(serialize_string(root_path, legacy=True))

    # mounted_path (legacy string)
    buffer.extend(serialize_string(mounted_path, legacy=True))

    # BLLLL (sesflags, root_uid, root_gid, map_all_uid, map_all_gid)
    buffer.extend(struct.pack(">BLLLL", sesflags, root_uid, root_gid, map_all_uid, map_all_gid))

    # BBLL (min_goal, max_goal, min_trash_time, max_trash_time)
    buffer.extend(struct.pack(">BBLL", min_goal, max_goal, min_trash_time, max_trash_time))

    # current_op_stats_list (L * stats_count)
    for stat in current_op_stats_list:
        buffer.extend(struct.pack(">L", stat))

    # last_hour_op_stats_list (L * stats_count)
    for stat in last_hour_op_stats_list:
        buffer.extend(struct.pack(">L", stat))

    return buffer

def serialize_mount_info(session_id: int, mount_info: str) -> bytes:
    """
    Serializes mount info for get_mounts_info.
    """
    buffer = bytearray()
    buffer.extend(struct.pack(">L", session_id))
    buffer.extend(serialize_string(mount_info, legacy=False)) # Mount info is V2 string
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