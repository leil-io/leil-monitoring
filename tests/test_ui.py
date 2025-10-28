from fastapi.testclient import TestClient
import pytest
from saunafs_monitoring.main import app, get_client
from saunafs_client.models import SystemInfo, ChunkHealth, Goal, MetadataServer, Mount
from saunafs_client import SAUNAFS_VERSION_WITH_INOTIFIERS_SUPPORT

client = TestClient(app)

# TODO(Urmas): Use environment variables
MASTER_HOST = "192.168.50.189"
MASTER_PORT = "9421"

master_version = get_client(MASTER_HOST, MASTER_PORT).master_version

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
        f"/sfs.cgi?masterhost={MASTER_HOST}&masterport={MASTER_PORT}&sections=IN|CS|HD|ML|MS|EX|MO|EX|CH|MC"
    )

    assert response.status_code == 200
    assert response.headers['content-type'] == 'text/html; charset=utf-8'
    assert "SaunaFS Info" in response.text
    assert "Info" in response.text
    assert "Chunk Servers" in response.text
    assert "Chunks state matrix" in response.text
    assert "Filesystem Check Info" in response.text
    assert "Metadata Servers" in response.text
    if master_version >= SAUNAFS_VERSION_WITH_INOTIFIERS_SUPPORT:
        assert "INotifier Loggers" in response.text
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
    response = client.get("/sfs.cgi?masterhost=nonexistant&masterport=9421")

    assert response.status_code == 200  # The page itself should still render
    assert "Can&#39;t connect to SaunaFS master" in response.text
