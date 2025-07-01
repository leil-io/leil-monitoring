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

class Mount(BaseModel):
    id: int
    session_id: int
    hostname: str
    ip_address: str
    mounted_path: str
    version: str
    mount_info: str

