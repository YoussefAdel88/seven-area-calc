"""
Tests for web server endpoints.
"""
import json
import tempfile
import pytest
from pathlib import Path
from src.web_server import app


@pytest.fixture
def client():
    """Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    """Test /health endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data
    assert data['status'] == 'ok'


def test_index_page_loads(client):
    """Test that the index page loads."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'SEVEN Area Calculator' in response.data
    assert b'Drag & drop' in response.data


def test_upload_no_file(client):
    """Test upload endpoint without file."""
    response = client.post('/api/upload')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'No file provided' in data['error']


def test_upload_wrong_extension(client):
    """Test upload with non-DXF file."""
    from io import BytesIO
    data = {
        'file': (BytesIO(b'test content'), 'test.txt')
    }
    response = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    result = json.loads(response.data)
    assert result['success'] is False
    assert '.dxf' in result['error'].lower()

