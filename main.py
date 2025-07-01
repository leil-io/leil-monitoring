from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import socket
import traceback
import logging
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


from saunafs_client import SaunaFSClient
from models import SystemInfo, Server, Disk

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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
    return client.get_system_info()

@app.get("/api/servers", response_model=List[Server])
async def api_get_servers(master_host: str = "127.0.0.1", master_port: int = 9421):
    client = get_client(master_host, master_port)
    return client.get_servers()

@app.get("/api/disks", response_model=List[Disk])
async def api_get_disks(master_host: str = "127.0.0.1", master_port: int = 9421):
    client = get_client(master_host, master_port)
    return client.get_disks()

# --- Legacy UI Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <html><head><meta http-equiv="refresh" content="0;url=/sfs.cgi" /></head>
    <body><p>Redirecting to <a href="/sfs.cgi">/sfs.cgi</a>.</p></body></html>
    """

@app.get("/sfs.cgi", response_class=HTMLResponse)
async def get_sfs_info(request: Request, masterhost: str = "127.0.0.1", masterport: int = 9421, mastername: str = "SaunaFS", sections: str = "IN|CS|HD|ML|MS"):
    try:
        client = get_client(masterhost, masterport)
        
        if client.master_version == (0, 0, 0):
            raise HTTPException(status_code=503, detail=f"Can't connect to SaunaFS master at {masterhost}:{masterport}")

        active_sections = sections.split("|")
        
        info_data = client.get_system_info() if "IN" in active_sections else None
        servers_data = client.get_servers() if "CS" in active_sections else None
        disks_data = client.get_disks() if "HD" in active_sections else None
        metaloggers_data = client.get_metaloggers() if "ML" in active_sections else None
        mounts_data = client.get_mounts() if "MS" in active_sections else None
        
        context = {
            "request": request, "mastername": mastername, "masterhost": masterhost,
            "masterport": masterport, "sections": active_sections,
            "info": info_data, "servers": servers_data, "disks": disks_data,
            "metaloggers": metaloggers_data, "mounts": mounts_data,
            "error_message": None
        }
        return templates.TemplateResponse("sfs.html", context)
    except Exception as e:
        traceback.print_exc()
        context = {"request": request, "mastername": mastername, "error_message": f"An internal error occurred: {e}", "sections": []}
        return templates.TemplateResponse("sfs.html", context)


@app.get("/chart.cgi")
async def get_chart(host: str, port: int, id: int):
    client = get_client("127.0.0.1", 9421) # Dummy client for now
    try:
        image_data = client.get_chart(host, port, id)
        media_type = "image/gif" if image_data.startswith(b"GIF") else "image/png"
        return Response(content=image_data, media_type=media_type)
    except Exception:
        with open("static/err.gif", "rb") as f:
            return Response(content=f.read(), media_type="image/gif")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
