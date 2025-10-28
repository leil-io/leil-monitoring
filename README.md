# SaunaFS CGI Rewrite (WIP)

## TODO:

- [x] Get goal definitions
- [x] Get chunk information
- [x] Get charts for master
- [x] Add tabs
- [x] Get charts for chunkservers
- [x] Add metalogger list
- [x] Add CI pipeline
- [x] Add chunkserver removal
- [x] Add disk scanning progress
- [x] Add legend to matrix table
- [x] Add missing stats for disks (Average block size etc.)
- [x] Add CD pipeline
- [ ] Do some more styling (arrows on chart etc.)
- [ ] Add switch between old and new theme (optional)
- [x] Add deb packaging (Absolutely optional)
- [x] Add wheel packaging (Absolutely optional)
- [ ] Add package delivery (Absolutely optional)

This directory contains a modern rewrite of the SaunaFS CGI monitoring interface using the FastAPI web framework.

## Setup and Installation (local)

### 1. Create a Virtual Environment

It is highly recommended to run this application in a Python virtual environment. From the root folder of the repository, run the following commands:

```bash
# Create the virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

### 2. Install Dependencies

With the virtual environment activated, install the required packages from `requirements.txt`.

```bash
pip install -r requirements.txt
```

## Running the Application (local)

After installing the dependencies, you can run either the `saunafs_api` or `saunafs_monitoring` application using `uvicorn`. For example, to start the monitoring tool (the process is similar for the API tool):

```bash
# The --reload flag will automatically restart the server when you make code changes.
uvicorn --host 0.0.0.0 --reload --app-dir src saunafs_monitoring.main:app
```

The application will be available at `http://127.0.0.1:8000`.

## Installing and Running the Application (docker)

Make sure docker is installed.

Copy the .env.example to .env and edit as needed. Note that the ports you set
will be a 1-1 mapping of for both the application and exposed port on host. If
you need different behaviour for some reason, edit the compose as needed.

```bash
docker compose build
docker compose [-d] up # Use -d if you want to detach
docker compose down # Destroys containers
```

For developers, you may use run-dev.sh script for quick iteration

## API

In addition to the legacy UI, this application also exposes a modern REST API. The interactive API documentation (provided by Swagger UI) is available at `http://127.0.0.1:8000/docs`.

## Package Distribution

This project now supports package distribution via:

### Building Packages

```shell
docker build \
    -t saunafs-monitoring:runtime-deb  \
    --target runtime-deb \
    --file Dockerfile.build \
    .
docker create --name temp saunafs-monitoring:runtime-deb
docker cp temp:/packages ./dist/
docker rm temp
```

### Available formats:

- `.deb` - System package (Ubuntu/Debian)
- `.whl` - Python wheel

### Installation from packages

```shell
# from .deb
sudo dpkg -i ./dist/saunafs-monitoring_1.0.0-python3.13_all.deb

# from .whl
pip install ./dist/saunafs_monitoring-1.0.0-py3-none-any.whl
```

### Run image with package deployed

You might build with `--target runtime` for a **python** image with the `wheel` package installed.  
If you prefer to use the **ubuntu** image with `deb` package, use `--target runtime-deb`.

```shell
# For wheel-based image (Python base)
docker build \
    -t saunafs-monitoring:runtime  \
    --target runtime \
    --file Dockerfile.build \
    .
docker run --name saunafs-monitoring saunafs-monitoring:runtime
```

```shell
# For deb-based image (Ubuntu base)
docker build \
    -t saunafs-monitoring:runtime  \
    --target runtime-deb \
    --file Dockerfile.build \
    .
docker run --name saunafs-monitoring saunafs-monitoring:runtime
```

### Image customization

You might want to customize the image to run a different module (e.g. `saunafs_api` instead of `saunafs_monitoring`). You can do this by passing a different command at runtime:

```shell
#For runtime target (Python base)
docker run -it saunafs-monitoring:runtime \
    /usr/local/bin/python3 -m saunafs_api.main

# For runtime-deb target (Ubuntu base)
docker run -it saunafs-monitoring:runtime \
    /usr/bin/python3 -m saunafs_api.main
```

The default command is `/usr/local/bin/python3 -m saunafs_monitoring.main` for the `runtime` target.

The default command is `/usr/bin/python3 -m saunafs_monitoring.main` for the `runtime-deb` target.

Notice that the python path is different between the two targets.
