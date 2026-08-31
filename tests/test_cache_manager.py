import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.cache_manager import CacheManager

TEST_CACHE_DIR = Path(__file__).parent / "_tmp_cache"


def setup_function():
    if TEST_CACHE_DIR.exists():
        shutil.rmtree(TEST_CACHE_DIR)


def teardown_function():
    if TEST_CACHE_DIR.exists():
        shutil.rmtree(TEST_CACHE_DIR)


def test_set_and_get_roundtrip():
    cache = CacheManager(cache_dir=TEST_CACHE_DIR)
    cache.set("agent1:complaint_123", {"normalized": True, "text": "example"})
    assert cache.get("agent1:complaint_123") == {"normalized": True, "text": "example"}


def test_missing_key_returns_none():
    cache = CacheManager(cache_dir=TEST_CACHE_DIR)
    assert cache.get("does_not_exist") is None
    assert cache.has("does_not_exist") is False


def test_persists_across_instances():
    cache = CacheManager(cache_dir=TEST_CACHE_DIR)
    cache.set("agent5:doc_impact", {"action": "CAPA"})

    reloaded = CacheManager(cache_dir=TEST_CACHE_DIR)
    assert reloaded.has("agent5:doc_impact") is True
    assert reloaded.get("agent5:doc_impact") == {"action": "CAPA"}
