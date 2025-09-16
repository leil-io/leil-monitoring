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
- [ ] Add legend to matrix table
- [ ] Add missing stats for disks (Average block size etc.)
- [ ] Add CD pipeline
- [ ] Do some more styling (arrows on chart etc.)
- [ ] Add switch between old and new theme (optional)
- [ ] Add deb packaging (Absolutely optional)

This directory contains a modern rewrite of the SaunaFS CGI monitoring interface using the FastAPI web framework.

## Setup and Installation (local)

### 1. Create a Virtual Environment

It is highly recommended to run this application in a Python virtual environment.

```bash
# Navigate to this directory
cd cgi-rewrite

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

Once the dependencies are installed, you can run the application using `uvicorn`.

```bash
# The --reload flag will automatically restart the server when you make code changes.
uvicorn main:app --reload
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
