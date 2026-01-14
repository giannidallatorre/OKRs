"""Test configuration validation."""
import json
import os
import pytest
from pathlib import Path

def test_service_account_exists():
    """Test that service account file exists in expected location"""
    config_path = Path(".config/service_account.json")
    assert config_path.exists(), f"Service account file not found at {config_path}"

def test_service_account_valid_json():
    """Test that service account is valid JSON"""
    with open(".config/service_account.json") as f:
        data = json.load(f)  # Will raise JSONDecodeError if invalid

def test_service_account_required_fields():
    """Test that service account has required structure"""
    with open(".config/service_account.json") as f:
        data = json.load(f)
        assert data.get("type") == "service_account", "Missing or invalid 'type' field"
        assert "@" in data.get("client_email", ""), "Invalid or missing client_email"
        assert data.get("private_key", "").startswith("-----BEGIN"), "Invalid private_key format"