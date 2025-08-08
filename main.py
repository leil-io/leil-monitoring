from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import socket
import traceback
import logging
from typing import List
from datetime import datetime
import pathlib
from saunafs_client import SaunaFSClient
from models import (
    SystemInfo, Server, Disk, Mount, MetadataServer, FsCheckInfo,
    ChunkOperationsInfo, OperationStats, ChunkMatrix, Goal, ChunkHealth,
    ChunkMappedHealth
)


# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = pathlib.Path(__file__).parent.resolve()


app = FastAPI()

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# --- Helper Functions ---


def humanize_bytes(num, suffix="B"):
    if not isinstance(num, (int, float)):
        return "N/A"
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Y{suffix}"


templates.env.filters["humanize_bytes"] = humanize_bytes


def format_timestamp(ts):
    if not isinstance(ts, int) or ts == 0:
        return "N/A"
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


templates.env.filters["format_timestamp"] = format_timestamp


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


# --- Legacy UI Endpoints ---
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_root():
    return RedirectResponse(url="/sfs.cgi")


@app.get("/sfs.cgi", response_class=HTMLResponse)
async def get_sfs_info(request: Request, masterhost: str = "127.0.0.1",
                       masterport: int = 9421, mastername: str = "SaunaFS",
                       sections: str = "IN"):
    try:
        client = get_client(masterhost, masterport)

        if client.master_version == (0, 0, 0):
            raise HTTPException(status_code=503, detail=f"Can't connect to SaunaFS master at {masterhost}:{masterport}")

        activeSections = sections.split("|")

        infoData = client.get_info() if "IN" in activeSections else None
        serversData = client.get_servers() if "CS" in activeSections or "CC" in activeSections else None
        disksData = client.get_disks() if "HD" in activeSections else None
        metaloggersData = client.get_metaloggers() if "ML" in activeSections else None
        mountsData = client.get_mounts() if "MS" in activeSections else None
        exportsData = client.get_exports() if "EX" in activeSections else None
        metadataServersData = client.get_metadata_servers() if "CS" in activeSections else None
        fsCheckInfoData = client.get_fs_check_info() if "IN" in activeSections else None
        chunkOperationsInfoData = client.get_chunk_operations_info() if "IN" in activeSections else None
        chunkMatrixData = client.get_chunk_matrix() if "IN" in activeSections else None
        goals = client.get_goals() if "EX" in activeSections else None
        chunks_health = client.get_chunk_health() if "CH" in activeSections else None
        op_names = list(OperationStats.model_fields.keys())

        goalmap = None
        replication_sums = None
        deletion_sums = None
        if chunks_health:
            if goals:
                goalmap = ChunkMappedHealth.from_chunk_health(chunks_health, goals)
            else:
                goalmap = ChunkMappedHealth.from_chunk_health(chunks_health, client.get_goals())
            replication_sums = get_goal_chunk_sums(goalmap, "replication")
            deletion_sums = get_goal_chunk_sums(goalmap, "deletion")

        context = {
            "request": request, "mastername": mastername, "masterhost": masterhost,
            "masterport": masterport, "sections": activeSections,
            "info": infoData, "servers": serversData, "disks": disksData,
            "metaloggers": metaloggersData, "mounts": mountsData, "exports": exportsData,
            "metadata_servers": metadataServersData,
            "fs_check_info": fsCheckInfoData,
            "chunk_operations_info": chunkOperationsInfoData,
            "chunk_matrix": chunkMatrixData,
            "op_names": op_names,
            "error_message": None,
            "chunks_health": chunks_health,
            "goalmap": goalmap,
            "goals": goals,
            "replication_sums": replication_sums,
            "deletion_sums": deletion_sums,
            "active_sections": activeSections
        }
        return templates.TemplateResponse(request, "sfs.html", context)
    except Exception as e:
        traceback.print_exc()
        context = {"request": request, "mastername": mastername, "error_message": f"An internal error occurred: {e}", "sections": []}
        return templates.TemplateResponse(request, "sfs.html", context)


@app.get("/chart.cgi")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
