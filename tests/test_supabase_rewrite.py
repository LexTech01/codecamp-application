import json
import os
import pytest
from unittest import mock

import config

DIRECT_URL = "postgresql://postgres:sekret123@db.ca5mple.supabase.co:5432/postgres"
POOLER_HOST = "aws-0-eu-west-1.pooler.supabase.com"


@pytest.fixture(autouse=True)
def fake_region(monkeypatch, tmp_path):
    ranges = {
        "ipv6_prefixes": [
            {"ipv6_prefix": "2a05:d018::/35", "region": "eu-west-1", "service": "AMAZON"},
            {"ipv6_prefix": "2600:1f14::/32", "region": "us-west-2", "service": "AMAZON"},
        ]
    }
    cache = tmp_path / "aws-ip-ranges.json"
    cache.write_text(json.dumps(ranges))
    monkeypatch.setattr(config, "_AWS_RANGES_CACHE", str(cache))
    return cache


@pytest.fixture(autouse=True)
def fake_dns(monkeypatch):
    def fake_getaddrinfo(host, port=0, family=0, *args, **kwargs):
        if host == "db.ca5mple.supabase.co":
            return [(0, 0, 0, 0, ("2a05:d018:1b65:3001:1940:ee73:ce5f:9a3c", 5432))]
        if host == POOLER_HOST:
            return [(0, 0, 0, 0, ("34.241.16.247", 5432))]
        raise OSError(f"Name or service not known: {host}")

    monkeypatch.setattr(config.socket, "getaddrinfo", fake_getaddrinfo)


def test_direct_url_rewritten_to_pooler():
    assert config.rewrite_supabase_direct_url(DIRECT_URL) == (
        f"postgresql://postgres.ca5mple:sekret123@{POOLER_HOST}:5432/postgres"
    )


def test_direct_url_with_query_keeps_query():
    url = DIRECT_URL + "?sslmode=require"
    rewritten = config.rewrite_supabase_direct_url(url)
    assert rewritten.startswith(f"postgresql://postgres.ca5mple:sekret123@{POOLER_HOST}:5432/postgres?")
    assert "sslmode=require" in rewritten


def test_non_supabase_url_unchanged():
    url = "postgresql://user:pass@db.example.com:5432/mydb"
    assert config.rewrite_supabase_direct_url(url) == url


def test_retired_pooler_host_unchanged():
    url = "postgresql://postgres:pass@db.ca5mple.pooler.supabase.com:6543/postgres"
    assert config.rewrite_supabase_direct_url(url) == url


def test_non_postgres_user_unchanged():
    url = "postgresql://custom_role:pass@db.ca5mple.supabase.co:5432/postgres"
    assert config.rewrite_supabase_direct_url(url) == url


def test_unknown_region_leaves_url_unchanged(monkeypatch, tmp_path):
    ranges = {"ipv6_prefixes": []}
    cache = tmp_path / "aws-ip-ranges.json"
    cache.write_text(json.dumps(ranges))
    monkeypatch.setattr(config, "_AWS_RANGES_CACHE", str(cache))
    assert config.rewrite_supabase_direct_url(DIRECT_URL) == DIRECT_URL


def test_dns_failure_leaves_url_unchanged(monkeypatch):
    def boom(host, *args, **kwargs):
        raise OSError("Name or service not known")

    monkeypatch.setattr(config.socket, "getaddrinfo", boom)
    assert config.rewrite_supabase_direct_url(DIRECT_URL) == DIRECT_URL


def test_aws_region_lookup_uses_cached_file():
    assert config._aws_region_for_ipv6("2a05:d018::1") == "eu-west-1"


def test_config_rewrite_happens_via_env(monkeypatch):
    import importlib

    fake_json = json.dumps({
        "ipv6_prefixes": [
            {"ipv6_prefix": "2a05:d018::/35", "region": "eu-west-1", "service": "AMAZON"},
        ]
    }).encode()
    fake_resp = mock.MagicMock()
    fake_resp.read.return_value = fake_json
    fake_resp.__enter__.return_value = fake_resp
    monkeypatch.setattr(config.os.path, "exists", lambda *a: False)
    monkeypatch.setattr(config.urllib.request, "urlopen", lambda *a, **k: fake_resp)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("DATABASE_URL", DIRECT_URL)
    cfg = importlib.reload(config).Config
    assert cfg.SQLALCHEMY_DATABASE_URI.startswith(
        f"postgresql://postgres.ca5mple:sekret123@{POOLER_HOST}:5432/postgres"
    )
    assert "sslmode=require" in cfg.SQLALCHEMY_DATABASE_URI

