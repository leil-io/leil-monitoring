from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import socket
import traceback
import logging
from typing import List
from datetime import datetime
from saunafs_client import SaunaFSClient
from saunafs_client.models import (
    SystemInfo, Server, Disk, Mount, MetadataServer, FsCheckInfo,
    ChunkOperationsInfo, OperationStats, ChunkMatrix, Goal, ChunkHealth,
    ChunkMappedHealth
)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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
async def api_get_info(masterhost: str = "127.0.0.1", masterport: int = 9421):
    client = get_client(masterhost, masterport)
    return client.get_info()


@app.get("/api/chunkhealth", response_model=ChunkHealth)
async def api_get_chunk_health(masterhost: str = "127.0.0.1", masterport: int = 9421):
    client = get_client(masterhost, masterport)
    return client.get_chunk_health()


@app.get("/api/servers", response_model=List[Server])
async def api_get_servers(masterhost: str = "127.0.0.1", masterport: int = 9421):
    client = get_client(masterhost, masterport)
    return client.get_servers()


@app.get("/api/disks", response_model=List[Disk])
async def api_get_disks(masterhost: str = "127.0.0.1", masterport: int = 9421):
    client = get_client(masterhost, masterport)
    return client.get_disks()


@app.get("/api/mounts", response_model=List[Mount])
async def api_get_mounts(masterhost: str = "127.0.0.1", masterport: int = 9421):
    client = get_client(masterhost, masterport)
    return client.get_mounts()


@app.get("/api/metadataservers", response_model=List[MetadataServer])
async def api_get_metadata_servers(masterhost: str = "127.0.0.1", masterport: int = 9421):
    client = get_client(masterhost, masterport)
    return client.get_metadata_servers()


@app.get("/api/fscheckinfo", response_model=FsCheckInfo)
async def api_get_fs_check_info(masterhost: str = "127.0.0.1", masterport: int = 9421):
    client = get_client(masterhost, masterport)
    return client.get_fs_check_info()


@app.get("/api/chunkoperationsinfo", response_model=ChunkOperationsInfo)
async def api_get_chunk_operations_info(masterhost: str = "127.0.0.1", masterport: int = 9421):
    client = get_client(masterhost, masterport)
    return client.get_chunk_operations_info()


@app.get("/api/goals", response_model=List[Goal])
async def api_get_goals(masterhost: str = "127.0.0.1", masterport: int = 9421):
    client = get_client(masterhost, masterport)
    return client.get_goals()


@app.get("/api/chunkmatrix", response_model=ChunkMatrix)
async def api_get_chunk_matrix(masterhost: str = "127.0.0.1", masterport: int = 9421):
    client = get_client(masterhost, masterport)
    return client.get_chunk_matrix()


@app.get("/charts")
async def get_chart(id: int, host: str = "127.0.0.1", port: int = 9421):
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
