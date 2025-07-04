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
    ChunkOperationsInfo, OperationStats, ChunkMatrix, Metalogger
)


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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


def get_client(master_host: str, master_port: int) -> SaunaFSClient:
    try:
        if master_host == "sfsmaster":
            master_host = socket.gethostbyname(master_host)
    except socket.gaierror:
        raise HTTPException(status_code=404, detail=f"Master host not found: {master_host}")
    return SaunaFSClient(master_host=master_host, master_port=master_port)

# --- API Endpoints ---


@app.get("/api/info", response_model=SystemInfo)
async def api_get_info(master_host: str = "127.0.0.1", master_port: int = 9421):
    client = get_client(master_host, master_port)
    return SystemInfo.get(client)


@app.get("/api/servers", response_model=List[Server])
async def api_get_servers(master_host: str = "127.0.0.1", master_port: int = 9421):
    client = get_client(master_host, master_port)
    return Server.get_list(client)


@app.get("/api/disks", response_model=List[Disk])
async def api_get_disks(master_host: str = "127.0.0.1", master_port: int = 9421):
    client = get_client(master_host, master_port)
    return Disk.get_list(client)


@app.get("/api/mounts", response_model=List[Mount])
async def api_get_mounts(master_host: str = "127.0.0.1", master_port: int = 9421):
    client = get_client(master_host, master_port)
    return client.get_mounts()


@app.get("/api/metadataservers", response_model=List[MetadataServer])
async def api_get_metadata_servers(master_host: str = "127.0.0.1", master_port: int = 9421):
    client = get_client(master_host, master_port)
    return client.get_metadata_servers()


@app.get("/api/fscheckinfo", response_model=FsCheckInfo)
async def api_get_fs_check_info(master_host: str = "127.0.0.1", master_port: int = 9421):
    client = get_client(master_host, master_port)
    return client.get_fs_check_info()


@app.get("/api/chunkoperationsinfo", response_model=ChunkOperationsInfo)
async def api_get_chunk_operations_info(master_host: str = "127.0.0.1", master_port: int = 9421):
    client = get_client(master_host, master_port)
    return client.get_chunk_operations_info()


@app.get("/api/chunkmatrix", response_model=ChunkMatrix)
async def api_get_chunk_matrix(master_host: str = "127.0.0.1", master_port: int = 9421):
    client = get_client(master_host, master_port)
    return client.get_chunk_matrix()


# --- Legacy UI Endpoints ---
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_root():
    return RedirectResponse(url="/sfs.cgi")


@app.get("/sfs.cgi", response_class=HTMLResponse)
async def get_sfs_info(request: Request, masterhost: str = "127.0.0.1", masterport: int = 9421, mastername: str = "SaunaFS", sections: str = "IN|CS|HD|ML|MS|EX|MO"):
    try:
        client = get_client(masterhost, masterport)

        if client.master_version == (0, 0, 0):
            raise HTTPException(status_code=503, detail=f"Can't connect to SaunaFS master at {masterhost}:{masterport}")

        activeSections = sections.split("|")

        infoData = SystemInfo.get(client) if "IN" in activeSections else None
        serversData = Server.get_list(client) if "CS" in activeSections else None
        disksData = Disk.get_list(client) if "HD" in activeSections else None
        metaloggersData = Metalogger.get_list(client) if "ML" in activeSections else None
        mountsData = client.get_mounts() if "MS" in activeSections or "MO" in activeSections else None
        exportsData = client.get_exports() if "EX" in activeSections else None
        metadataServersData = client.get_metadata_servers() if "CS" in activeSections else None
        fsCheckInfoData = client.get_fs_check_info() if "IN" in activeSections else None
        chunkOperationsInfoData = client.get_chunk_operations_info() if "IN" in activeSections else None
        chunkMatrixData = client.get_chunk_matrix() if "IN" in activeSections else None

        op_names = list(OperationStats.model_fields.keys())

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
            "error_message": None
        }
        return templates.TemplateResponse(request, "sfs.html", context)
    except Exception as e:
        traceback.print_exc()
        context = {"request": request, "mastername": mastername, "error_message": f"An internal error occurred: {e}", "sections": []}
        return templates.TemplateResponse(request, "sfs.html", context)


@app.get("/chart.cgi")
async def get_chart(host: str, port: int, id: int):
    client = get_client("127.0.0.1", 9421)  # Dummy client for now
    try:
        imageData = client.get_chart(host, port, id)
        mediaType = "image/gif" if imageData.startswith(b"GIF") else "image/png"
        return Response(content=imageData, media_type=mediaType)
    except Exception:
        with open("static/err.gif", "rb") as f:
            return Response(content=f.read(), media_type="image/gif")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
