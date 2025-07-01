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
from models import SystemInfo, Server, Disk, Mount

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Helper Functions ---
def HumanizeBytes(num, suffix="B"):
    if not isinstance(num, (int, float)):
        return "N/A"
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Y{suffix}"

templates.env.filters["humanize_bytes"] = HumanizeBytes

def GetClient(masterHost: str, masterPort: int) -> SaunaFSClient:
    try:
        if masterHost == "sfsmaster":
            masterHost = socket.gethostbyname(masterHost)
    except socket.gaierror:
        raise HTTPException(status_code=404, detail=f"Master host not found: {masterHost}")
    return SaunaFSClient(masterHost=masterHost, masterPort=masterPort)

# --- API Endpoints ---
@app.get("/api/info", response_model=SystemInfo)
async def ApiGetInfo(masterHost: str = "127.0.0.1", masterPort: int = 9421):
    client = GetClient(masterHost, masterPort)
    return client.GetSystemInfo()

@app.get("/api/servers", response_model=List[Server])
async def ApiGetServers(masterHost: str = "127.0.0.1", masterPort: int = 9421):
    client = GetClient(masterHost, masterPort)
    return client.GetServers()

@app.get("/api/disks", response_model=List[Disk])
async def ApiGetDisks(masterHost: str = "127.0.0.1", masterPort: int = 9421):
    client = GetClient(masterHost, masterPort)
    return client.GetDisks()


@app.get("/api/mounts", response_model=List[Mount])
async def ApiGetMounts(masterHost: str = "127.0.0.1", masterPort: int = 9421):
    client = GetClient(masterHost, masterPort)
    return client.GetMounts()

# --- Legacy UI Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def ReadRoot():
    return """
    <html><head><meta http-equiv="refresh" content="0;url=/sfs.cgi" /></head>
    <body><p>Redirecting to <a href="/sfs.cgi">/sfs.cgi</a>.</p></body></html>
    """

@app.get("/sfs.cgi", response_class=HTMLResponse)
async def GetSfsInfo(request: Request, masterhost: str = "127.0.0.1", masterport: int = 9421, mastername: str = "SaunaFS", sections: str = "IN|CS|HD|ML|MS|EX"):
    try:
        client = GetClient(masterhost, masterport)

        if client.masterVersion == (0, 0, 0):
            raise HTTPException(status_code=503, detail=f"Can't connect to SaunaFS master at {masterhost}:{masterport}")

        activeSections = sections.split("|")

        infoData = client.GetSystemInfo() if "IN" in activeSections else None
        serversData = client.GetServers() if "CS" in activeSections else None
        disksData = client.GetDisks() if "HD" in activeSections else None
        metaloggersData = client.GetMetaloggers() if "ML" in activeSections else None
        mountsData = client.GetMounts() if "MS" in activeSections else None
        exportsData = client.GetExports() if "EX" in activeSections else None

        context = {
            "request": request, "mastername": mastername, "masterhost": masterhost,
            "masterport": masterport, "sections": activeSections,
            "info": infoData, "servers": serversData, "disks": disksData,
            "metaloggers": metaloggersData, "mounts": mountsData, "exports": exportsData,
            "error_message": None
        }
        return templates.TemplateResponse("sfs.html", context)
    except Exception as e:
        traceback.print_exc()
        context = {"request": request, "mastername": mastername, "error_message": f"An internal error occurred: {e}", "sections": []}
        return templates.TemplateResponse("sfs.html", context)


@app.get("/chart.cgi")
async def GetChart(host: str, port: int, id: int):
    client = GetClient("127.0.0.1", 9421) # Dummy client for now
    try:
        imageData = client.GetChart(host, port, id)
        mediaType = "image/gif" if imageData.startswith(b"GIF") else "image/png"
        return Response(content=imageData, media_type=mediaType)
    except Exception:
        with open("static/err.gif", "rb") as f:
            return Response(content=f.read(), media_type="image/gif")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
