from fastapi.testclient import TestClient
import pytest
from saunafs_monitoring.main import app
from saunafs_client.models import SystemInfo, ChunkHealth, Goal, MetadataServer, Mount

client = TestClient(app)


def test_read_root_redirects():
    """
    Tests that the root path '/' correctly redirects to '/sfs.cgi'.
    """
    response = client.get("/", follow_redirects=True)
    # TestClient follows redirects by default, so we check the history
    assert len(response.history) == 1
    assert response.history[0].status_code == 307  # Temporary Redirect
    assert response.url == "http://testserver/sfs.cgi"
    assert response.status_code == 200


@pytest.mark.integration
def test_get_sfs_info_html():
    """
    Tests that the main HTML page for the legacy UI renders successfully.
    """
    response = client.get(
        "/sfs.cgi?masterhost=localhost&masterport=9421&sections=IN|CS|HD|ML|MS|EX|MO|EX|CH|MC"
    )

    assert response.status_code == 200
    assert response.headers['content-type'] == 'text/html; charset=utf-8'
    assert "SaunaFS Info" in response.text
    assert "Info" in response.text
    assert "Chunk Servers" in response.text
    assert "Chunks state matrix" in response.text
    assert "Filesystem Check Info" in response.text
    assert "Metadata Servers" in response.text
    assert "Chunk Servers" in response.text
    assert "Disks" in response.text
    assert "Connected Clients" in response.text
    assert "Operations" in response.text
    assert "Exports" in response.text
    assert "Metadata Backup Loggers" in response.text
    assert "Goals" in response.text
    assert "Chunk Statistics" in response.text


@pytest.mark.integration
def test_get_sfs_info_connection_error():
    """
    Tests how the HTML page responds when it can't connect to the master.
    """
    # Use a port that is unlikely to be open
    response = client.get("/sfs.cgi?masterhost=localhost&masterport=9999")

    assert response.status_code == 200  # The page itself should still render
    assert "Can&#39;t connect to SaunaFS master" in response.text
