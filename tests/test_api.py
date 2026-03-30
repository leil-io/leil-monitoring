"""
This file is part of saunafs-monitoring.
Copyright (C) 2025 Leil Storage OÜ

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from fastapi.testclient import TestClient
import os
import pytest
import csv
from saunafs_api.main import app
from saunafs_client.models import Metalogger, SystemInfo, ChunkHealth, Goal, MetadataServer, Mount

client = TestClient(app)

MASTER_HOST = os.getenv("SAUNAFS_MASTER_HOST", "127.0.0.1")
MASTER_PORT = os.getenv("SAUNAFS_MASTER_PORT", "9421")


def test_read_root_api_redirects():
    """
    Tests that the root path '/' correctly redirects to '/docs'.
    """
    response = client.get("/", follow_redirects=True)
    # TestClient follows redirects by default, so we check the history
    assert len(response.history) == 1
    assert response.history[0].status_code == 307  # Temporary Redirect
    assert response.url == "http://testserver/docs"
    assert response.status_code == 200


@pytest.mark.integration
def test_api_get_info():
    """
    Tests the /api/info endpoint against a live master server.
    """
    response = client.get(f"/api/info?masterhost={MASTER_HOST}&masterport={MASTER_PORT}")

    assert response.status_code == 200

    # Validate the response against the Pydantic model
    system_info = SystemInfo(**response.json())

    assert isinstance(system_info, SystemInfo)
    assert system_info.version is not None
    assert system_info.total_space > 0


@pytest.mark.integration
def test_api_get_goals():
    """
    Tests the /api/goals endpoint against a live master server.
    """
    response = client.get(f"/api/goals?masterhost={MASTER_HOST}&masterport={MASTER_PORT}")

    assert response.status_code == 200

    # Validate the response against the Pydantic model
    goals = [Goal.model_validate(goal) for goal in response.json()]

    assert isinstance(goals, list)
    assert goals is not None
    assert all(isinstance(goal, Goal) for goal in goals)
    assert len(goals) > 0
    assert goals[0].id == 1


@pytest.mark.integration
def test_api_get_metadata_servers():
    """
    Tests the /api/metadataservers endpoint against a live master server.
    """
    response = client.get(f"/api/metadataservers?masterhost={MASTER_HOST}&masterport={MASTER_PORT}")

    assert response.status_code == 200

    # Validate the response against the Pydantic model
    metadata_servers = [MetadataServer.model_validate(server) for server in response.json()]

    assert isinstance(metadata_servers, list)
    assert metadata_servers is not None
    assert all(isinstance(server, MetadataServer) for server in metadata_servers)
    assert len(metadata_servers) > 0
    assert metadata_servers[0].personality == "master"


@pytest.mark.integration
def test_api_get_chunk_health():
    """
    Tests the /api/chunkhealth endpoint against a live master server.
    """
    response = client.get(f"/api/chunkhealth?masterhost={MASTER_HOST}&masterport={MASTER_PORT}")

    assert response.status_code == 200

    chunk_health = ChunkHealth(**response.json())

    assert isinstance(chunk_health, ChunkHealth)


@pytest.mark.integration
def test_get_mounts():
    """
    Tests the /api/mounts endpoint against a live master server
    """
    response = client.get(f"/api/mounts?masterhost={MASTER_HOST}&masterport={MASTER_PORT}")

    assert response.status_code == 200
    # Validate the response against the Pydantic model
    mounts = [Mount.model_validate(mount) for mount in response.json()]
    assert all(isinstance(mount, Mount) for mount in mounts)

@pytest.mark.integration
def test_get_metaloggers():
    """
    Tests the /api/metaloggers endpoint against a live master server
    """
    response = client.get(f"/api/metaloggers?masterhost={MASTER_HOST}&masterport={MASTER_PORT}")

    if response.status_code == 404:
        pytest.skip("metaloggers api endpoint not found")
    assert response.status_code == 200
    # Validate the response against the Pydantic model
    metaloggers = [Metalogger.model_validate(meta) for meta in response.json()]
    assert all(isinstance(meta, Metalogger) for meta in metaloggers)


@pytest.mark.integration
def test_get_chart_csv_right_range():
    """
    Tests the chart CSV endpoint against a live master server, making sure the
    ranges are valid
    """
    ids = [
        90060,
        90051,
        90042,
        90033,
    ]
    responses = [
    ]
    for id in ids:
        responses.append(client.get(f"/api/cgicharts?id={id}&host={MASTER_HOST}&port={MASTER_PORT}"))

    for indx, response in enumerate(responses):
        assert response.status_code == 200
        timestamps = []
        csv_reader = csv.reader(response.text.strip().splitlines())
        # Skip header
        next(csv_reader)
        for row in csv_reader:
            assert row[0].isdigit()
            timestamps.append(int(row[0]))

        id_range = int(ids[indx]) % 90000 % 10
        last_timestamp = 0
        for i in range(1, len(timestamps)):
            if last_timestamp == 0:
                last_timestamp = timestamps[i]
                continue
            if id_range == 0:
                assert timestamps[i] - last_timestamp == 60
            elif id_range == 1:
                assert timestamps[i] - last_timestamp == 360
            elif id_range == 2:
                assert timestamps[i] - last_timestamp == 1800
            elif id_range == 3:
                assert timestamps[i] - last_timestamp == 86400
            else:
                raise Exception(f"Unexpected range {id_range}")
            last_timestamp = timestamps[i]
