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

def test_cli_workers_singular():
	sys.argv = original_argv + ['--mirror', '*', '--workers', '1', '--tier0', f"https://torxed:{os.environ['PASSWORD']}@repos.archlinux.org/$repo/os/$arch"]

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

def test_cli_parse():
	sys.argv = original_argv + ['--parse']

	test_data = ''
	test_data += '1678652796.0924394,http://mirror.reisenbauer.ee/archlinux,-2,"<urlopen error [Errno -5] No address associated with hostname>"\n'
	test_data += '1678652796.2621465,http://archlinux.mirror.colo-serv.net,-2,"<urlopen error [Errno -2] Name or service not known>"\n'
	test_data += '1678652796.3114855,http://mirror.easyname.at/archlinux,75474.0,"20:57:54"\n'
	test_data += '1678652796.3470361,http://archlinux.mirror.kangaroot.net,904879.0,"10 days, 11:21:19"\n'
	test_data += '1678652796.3646152,http://mirrors.netix.net/archlinux,13515.0,"3:45:15"\n'
	test_data += '1678653128.7254856,http://mirror.lebedinets.ru/archlinux,-4,"1 validation error for MirrorTester\n'
	test_data += '__root__\n'
	test_data += '  invalid literal for int() with base 10: b\'<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta http-equiv="X-UA-Compatible" content="IE=edge">\n    <meta name="viewport" content="width=device-width, initial-scale (type=value_error)"\'\n'

	with open('./output_1678652848.097852.log', 'w') as fh:
		fh.write(test_data)

	import mirrortest.tooling.cli

	importlib.reload(mirrortest.tooling.cli)

	mirrortest.tooling.cli.run()

def test_cli_stats():
	sys.argv = original_argv + ['--stats']

	import mirrortest.tooling.cli

	importlib.reload(mirrortest.tooling.cli)

	mirrortest.tooling.cli.run()

def test_cli_stats_verbose():
	sys.argv = original_argv + ['--stats', '--verbose']

	import mirrortest.tooling.cli

	importlib.reload(mirrortest.tooling.cli)

	mirrortest.tooling.cli.run()