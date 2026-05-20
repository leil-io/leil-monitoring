"""
This file is part of leil-monitoring.
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
from leil_monitoring.main import app

client = TestClient(app)

MASTER_HOST = os.getenv("SAUNAFS_MASTER_HOST", "127.0.0.1")
MASTER_PORT = os.getenv("SAUNAFS_MASTER_PORT", "9421")

def test_read_root_redirects():
    """
    Tests that the root path '/' correctly redirects to '/leil.cgi'.
    """
    response = client.get("/", follow_redirects=True)
    # TestClient follows redirects by default, so we check the history
    assert len(response.history) == 1
    assert response.history[0].status_code == 307  # Temporary Redirect
    assert response.url == "http://testserver/leil.cgi"
    assert response.status_code == 200


@pytest.mark.integration
def test_get_leil_info_html():
    """
    Tests that the main HTML page for the legacy UI renders successfully.
    """
    response = client.get(
        f"/leil.cgi?masterhost={MASTER_HOST}&masterport={MASTER_PORT}&sections=IN|CS|HD|ML|MS|EX|MO|EX|CH|MC"
    )

    assert response.status_code == 200
    assert response.headers['content-type'] == 'text/html; charset=utf-8'
    assert "LeilFS Info" in response.text
    assert "Info" in response.text
    assert "Chunk Servers" in response.text
    assert "Chunks state matrix" in response.text
    assert "Filesystem Check Info" in response.text
    assert "Metadata Servers" in response.text
    assert "Disks" in response.text
    assert "Connected Clients" in response.text
    assert "Operations" in response.text
    assert "Exports" in response.text
    assert "Metadata Backup Loggers" in response.text
    assert "Goals" in response.text
    assert "Chunk Statistics" in response.text


@pytest.mark.integration
def test_get_leil_info_connection_error():
    """
    Tests how the HTML page responds when it can't connect to the master.
    """
    # Use a port that is unlikely to be open
    response = client.get("/leil.cgi?masterhost=nonexistant&masterport=9421")

    assert response.status_code == 200  # The page itself should still render
    assert "Can&#39;t connect to LeilFS master" in response.text
