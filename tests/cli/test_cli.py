import pytest
import datetime
import sys
import importlib

original_argv = sys.argv

def test_cli_single():
	sys.argv = original_argv + ['--mirror', 'https://mirror.pseudoform.org/']

	import mirrortest.tooling.cli

	mirrortest.tooling.cli.run()

def test_cli_workers():
	sys.argv = original_argv + ['--mirror', '*', '--workers', '2']

	import mirrortest.tooling.cli

	importlib.reload(mirrortest.tooling.cli)

	mirrortest.tooling.cli.run()

def test_cli_single_URLError():
	sys.argv = original_argv + ['--mirror', 'https://broken.lan/']

	import mirrortest.tooling.cli

	importlib.reload(mirrortest.tooling.cli)

	mirrortest.tooling.cli.run()

def test_cli_single_HTTPError():
	sys.argv = original_argv + ['--mirror', 'https://archlinux.org/404_url']

	import mirrortest.tooling.cli

	importlib.reload(mirrortest.tooling.cli)

	mirrortest.tooling.cli.run()