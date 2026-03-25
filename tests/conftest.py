#!/usr/bin/env python3
"""Shared pytest configuration and fixtures."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "patches"))

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "repo")

import pytest

@pytest.fixture
def repo_root():
    return REPO_ROOT

@pytest.fixture
def skill_path():
    def _get(name):
        return os.path.join(REPO_ROOT, name)
    return _get

@pytest.fixture
def read_skill():
    def _read(name, filename):
        fpath = os.path.join(REPO_ROOT, name, filename)
        if not os.path.exists(fpath):
            return None
        with open(fpath) as f:
            return f.read()
    return _read
