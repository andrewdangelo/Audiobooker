"""
Tests for audiobook endpoints
"""

import pytest


def test_get_audiobooks(client):
    """Test getting list of audiobooks"""
    response = client.get("/api/v1/audiobooks/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_get_audiobook_not_found(client):
    """Test getting non-existent audiobook"""
    response = client.get("/api/v1/audiobooks/nonexistent")
    assert response.status_code == 404


# TODO: Add more tests
# - test_create_audiobook
# - test_update_audiobook
# - test_delete_audiobook
