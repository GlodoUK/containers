"""Tests for the shared utils module."""

import subprocess

import pytest

from odoo_kopia_snapshot.utils import run_command


def test_run_command_success():
    result = run_command(["echo", "hello"], capture_output=True)
    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 0
    assert result.stdout.strip() == "hello"


def test_run_command_check_true_raises():
    with pytest.raises(subprocess.CalledProcessError):
        run_command(["false"], check=True)


def test_run_command_check_false_returns_completed_process():
    result = run_command(["false"], check=False)
    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode != 0
