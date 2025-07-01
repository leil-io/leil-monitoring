from pydantic import BaseModel
from typing import List, Optional

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

class Disk(BaseModel):
    path: str
    status: str
    last_error: str
    total_space: int
    used_space: int
    chunks: int

class Metalogger(BaseModel):
    id: int
    hostname: str
    ip_address: str
    version: str


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

