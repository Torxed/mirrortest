import pytest
import datetime
import sys
import importlib
import os

original_argv = sys.argv

def test_cli_single():
	sys.argv = original_argv + ['--mirror', 'https://mirror.pseudoform.org/', '--tier0', f"https://torxed:{os.environ['PASSWORD']}@repos.archlinux.org/$repo/os/$arch"]

	import mirrortest.tooling.cli

	mirrortest.tooling.cli.run()

def test_cli_workers():
	sys.argv = original_argv + ['--mirror', '*', '--workers', '2', '--tier0', f"https://torxed:{os.environ['PASSWORD']}@repos.archlinux.org/$repo/os/$arch"]

	import mirrortest.tooling.cli

	importlib.reload(mirrortest.tooling.cli)

	mirrortest.tooling.cli.run()

def test_cli_single_URLError():
	sys.argv = original_argv + ['--mirror', 'https://broken.lan/', '--tier0', f"https://torxed:{os.environ['PASSWORD']}@repos.archlinux.org/$repo/os/$arch"]

	import mirrortest.tooling.cli

	importlib.reload(mirrortest.tooling.cli)

	mirrortest.tooling.cli.run()

def test_cli_single_HTTPError():
	sys.argv = original_argv + ['--mirror', 'https://archlinux.org/404_url', '--tier0', f"https://torxed:{os.environ['PASSWORD']}@repos.archlinux.org/$repo/os/$arch"]

	import mirrortest.tooling.cli

	importlib.reload(mirrortest.tooling.cli)

	mirrortest.tooling.cli.run()