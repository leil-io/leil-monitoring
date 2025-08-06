# SaunaFS CGI Rewrite (WIP)

## TODO:

- [x] Get goal definitions
- [x] Get chunk information
- [x] Get charts for master
- [x] Add tabs
- [ ] Add metalogger list
- [ ] Get charts for chunkservers
- [ ] Add chunkserver removal
- [ ] Add disk scanning progress
- [ ] Add legend to matrix table
- [ ] Add switch between old and new theme

This directory contains a modern rewrite of the SaunaFS CGI monitoring interface using the FastAPI web framework.

## Setup and Installation

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

## Running the Application

Once the dependencies are installed, you can run the application using `uvicorn`.

```bash
# The --reload flag will automatically restart the server when you make code changes.
uvicorn main:app --reload
```

The application will be available at `http://127.0.0.1:8000`.

## API

In addition to the legacy UI, this application also exposes a modern REST API. The interactive API documentation (provided by Swagger UI) is available at `http://127.0.0.1:8000/docs`.
