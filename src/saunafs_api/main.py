#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response, RedirectResponse
import socket
import traceback
import logging
import os
from typing import List
from datetime import datetime
from saunafs_client import SaunaFSClient
from saunafs_client.models import (
    SystemInfo, Server, Disk, Mount, MetadataServer, FsCheckInfo,
    ChunkOperationsInfo, ChunkMatrix, Goal, ChunkHealth,
    ChunkMappedHealth
)

SAUNAFS_MASTER_HOST = os.getenv("SAUNAFS_MASTER_HOST", "sfsmaster")
SAUNAFS_MASTER_PORT = int(os.getenv("SAUNAFS_MASTER_PORT", 9421))
SAUNAFS_API_LOGLEVEL = os.getenv("SAUNAFS_API_LOGLEVEL", "INFO")
SAUNAFS_API_HOST = os.getenv("SAUNAFS_API_HOST", "0.0.0.0")
SAUNAFS_API_PORT = int(os.getenv("SAUNAFS_API_PORT", 8001))

# Configure logging
logging.basicConfig(level=SAUNAFS_API_LOGLEVEL, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

# --- Helper Functions ---


def humanize_bytes(num, suffix="B"):
    if not isinstance(num, (int, float)):
        return "N/A"
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Y{suffix}"


def format_timestamp(ts):
    if not isinstance(ts, int) or ts == 0:
        return "N/A"
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


def get_client(masterhost: str, masterport: int) -> SaunaFSClient:
    try:
        if masterhost == "sfsmaster":
            masterhost = socket.gethostbyname(masterhost)
    except socket.gaierror:
        raise HTTPException(status_code=404, detail=f"Master host not found: {masterhost}")
    return SaunaFSClient(master_host=masterhost, master_port=masterport)


def get_goal_chunk_sums(goals: List[ChunkMappedHealth], attribute: str) -> List[int]:
    sums = []
    for i in range(11):
        total = 0
        for goal in goals:
            if goal.replication:  # Equivalent to len(goal.replication) > 0
                total += getattr(goal, attribute)[i]
        sums.append(total)

    return sums

# --- API Endpoints ---


@app.get("/api/info", response_model=SystemInfo)
async def api_get_info(masterhost: str = SAUNAFS_MASTER_HOST, masterport: int = SAUNAFS_MASTER_PORT):
    client = get_client(masterhost, masterport)
    return client.get_info()


@app.get("/api/chunkhealth", response_model=ChunkHealth)
async def api_get_chunk_health(masterhost: str = SAUNAFS_MASTER_HOST, masterport: int = SAUNAFS_MASTER_PORT):
    client = get_client(masterhost, masterport)
    return client.get_chunk_health()


@app.get("/api/servers", response_model=List[Server])
async def api_get_servers(masterhost: str = SAUNAFS_MASTER_HOST, masterport: int = SAUNAFS_MASTER_PORT):
    client = get_client(masterhost, masterport)
    return client.get_servers()


@app.get("/api/disks", response_model=List[Disk])
async def api_get_disks(masterhost: str = SAUNAFS_MASTER_HOST, masterport: int = SAUNAFS_MASTER_PORT):
    client = get_client(masterhost, masterport)
    return client.get_disks()


@app.get("/api/mounts", response_model=List[Mount])
async def api_get_mounts(masterhost: str = SAUNAFS_MASTER_HOST, masterport: int = SAUNAFS_MASTER_PORT):
    client = get_client(masterhost, masterport)
    return client.get_mounts()


@app.get("/api/metadataservers", response_model=List[MetadataServer])
async def api_get_metadata_servers(masterhost: str = SAUNAFS_MASTER_HOST, masterport: int = SAUNAFS_MASTER_PORT):
    client = get_client(masterhost, masterport)
    return client.get_metadata_servers()


@app.get("/api/fscheckinfo", response_model=FsCheckInfo)
async def api_get_fs_check_info(masterhost: str = SAUNAFS_MASTER_HOST, masterport: int = SAUNAFS_MASTER_PORT):
    client = get_client(masterhost, masterport)
    return client.get_fs_check_info()


@app.get("/api/chunkoperationsinfo", response_model=ChunkOperationsInfo)
async def api_get_chunk_operations_info(masterhost: str = SAUNAFS_MASTER_HOST, masterport: int = SAUNAFS_MASTER_PORT):
    client = get_client(masterhost, masterport)
    return client.get_chunk_operations_info()


@app.get("/api/goals", response_model=List[Goal])
async def api_get_goals(masterhost: str = SAUNAFS_MASTER_HOST, masterport: int = SAUNAFS_MASTER_PORT):
    client = get_client(masterhost, masterport)
    return client.get_goals()


@app.get("/api/chunkmatrix", response_model=ChunkMatrix)
async def api_get_chunk_matrix(masterhost: str = SAUNAFS_MASTER_HOST, masterport: int = SAUNAFS_MASTER_PORT):
    client = get_client(masterhost, masterport)
    return client.get_chunk_matrix()


@app.get("/charts")
async def get_chart(id: int, host: str = SAUNAFS_MASTER_HOST, port: int = SAUNAFS_MASTER_PORT):
    client = get_client(host, port)
    try:
        image_data = client.get_chart(host, port, id)
        media_type = ""
        if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
            media_type = "image/png"
        elif image_data.startswith(b"timestamp"):
            media_type = "text/plain"
        elif image_data.startswith(b"GIF"):
            media_type = "image/gif"
        else:
            raise Exception(f"unknown data: {image_data}")

        logging.debug(f"returning media_type: {media_type}")
        return Response(content=bytes(image_data), media_type=media_type)
    except Exception as e:
        logging.error(f"Could not get charts {e}")
        traceback.print_exc()
        with open("static/err.gif", "rb") as f:
            return Response(content=f.read(), media_type="image/gif")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_root():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    logging.log(logging.DEBUG, f"api host={SAUNAFS_API_HOST}, port={SAUNAFS_API_PORT}")
    uvicorn.run(app, host=SAUNAFS_API_HOST, port=SAUNAFS_API_PORT)
