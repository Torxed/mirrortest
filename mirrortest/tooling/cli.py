import dataclasses
import argparse
import pathlib
import json
import csv
import time
import sys
import glob
import sqlite3
import urllib.error
import urllib.request
import pydantic
import threading
import functools
import datetime

from ..models import (
	MirrorTester,
	Tier0
)

from ..mailhandle import mailto
from ..session import configuration


class MirrorTesterThreading(threading.Thread):
	def __init__(self, frozen_mirror :functools.partial[MirrorTester]):
		threading.Thread.__init__(self)

		self.tester = frozen_mirror
		self.mirror_tester = None
		self.good_exit = None
		self.time_delta_str = None
		self.time_delta_int = None
		self.start()

	def run(self):
		try:
			self.mirror_tester = self.tester()
			self.good_exit = self.mirror_tester.valid

			if self.mirror_tester and (last_update := self.mirror_tester.last_update) and (tier0_last_update := self.mirror_tester.tier_0.last_update):  # type: ignore
				self.time_delta_str = tier0_last_update - last_update
				if type(self.time_delta_str) == datetime.timedelta:
					self.time_delta_int = self.time_delta_str.total_seconds()
				else:  # pragma: no cover
					self.time_delta_int = -5
			else:  # pragma: no cover
				self.time_delta_str = 'Could not find /lastupdate on mirror'
				self.time_delta_int = -6
		except urllib.error.HTTPError as error:  # pragma: no cover
			self.good_exit = False
			self.time_delta_str = str(error)
			self.time_delta_int = -1
		except urllib.error.URLError as error:  # pragma: no cover
			self.good_exit = False
			self.time_delta_str = str(error)
			self.time_delta_int = -2
		except TimeoutError as error:  # pragma: no cover
			self.good_exit = False
			self.time_delta_str = str(error)
			self.time_delta_int = -3
		except pydantic.error_wrappers.ValidationError as error:  # pragma: no cover
			self.good_exit = False
			self.time_delta_str = str(error)
			self.time_delta_int = -4

		if self.good_exit is None:  # pragma: no cover 
			self.good_exit = False


# Parse script arguments and use defaults from configuration where needed
main_options = argparse.ArgumentParser(description="Test the health of a given mirror.", add_help=True)
main_options.add_argument(
	"--tier",
	type=int,
	default=1,
	nargs="?",
	help="Dictates what Tier the mirror you're testing is"
)
main_options.add_argument(
	"--mirror",
	required=False,
	default=None,
	type=str,
	nargs="?",
	help="The URL of a mirror you would like to test"
)
# --tier0 is only required on the first run to set the credentials
# after which it's saved in ~/.config/mirrortester/config.json
# (apologies for the long line, but it looks visually appalling broken up)
main_options.add_argument(
	"--tier0",
	required=True if not all([configuration.USERNAME, configuration.PASSWORD]) else False,
	default=None if not all([configuration.USERNAME, configuration.PASSWORD]) else f"https://{configuration.USERNAME}:{configuration.PASSWORD}@repos.archlinux.org/$repo/os/$arch",
	type=str,
	nargs="?",
	help="Sets the TIER0 URL (https://<user>:<password>@repos.archlinux.org)"
)
main_options.add_argument(
	"--mail",
	required=False,
	default=False,
	action="store_true",
	help="Attempts to open your mail client of choice with a prepped message"
)
main_options.add_argument(
	"--workers",
	required=False,
	default=1,
	type=int,
	nargs="?",
	help="When --mirror is set to '*', how many paralell workers do you want?"
)
main_options.add_argument(
	"--parse",
	required=False,
	default=False,
	action="store_true",
	help="Parse a CSV log from a previous result and create a result database"
)
main_options.add_argument(
	"--stats",
	required=False,
	default=False,
	action="store_true",
	help="Print statistics from a parsed result database"
)
main_options.add_argument(
	"--verbose",
	required=False,
	default=False,
	action="store_true",
	help="Increse output verbosity"
)
args, unknown = main_options.parse_known_args()
configuration.email = args.mail


def run():
	tier_0 = Tier0(url=args.tier0)

	if args.mirror == '*':
		# Retrieve complete mirror list
		response = urllib.request.urlopen("https://archlinux.org/mirrorlist/all/")
		data = response.read()
		workers :list[MirrorTesterThreading] = []

		with open(f'output_{time.time()}.log', 'w') as log:
			for server in data.split(b'\n'):

				if b'#Server = ' not in server:
					continue
				elif len(server.strip()) == 0:  # pragma: no cover
					continue

				if server.startswith(b'#Server'):
					_, url = server.split(b'=', 1)
					url, _ = url.split(b'/$repo', 1)
					url = url.strip().decode()

					while len(workers) >= args.workers and not any([worker.good_exit is not None for worker in workers]):
						time.sleep(0.025)
						if "pytest" in sys.modules:
							break

					finished_worker = None
					for index, worker in enumerate(workers):
						if worker.good_exit is not None:
							finished_worker = workers.pop(index)
							break

					# Spawn a new worker
					workers.append(MirrorTesterThreading(functools.partial(MirrorTester, tier=2, url=url, tier_0=tier_0)))

					# And process the old one
					if finished_worker is None:
						continue

					if not finished_worker.good_exit:  # pragma: no cover
						log.write(f"{time.time()},{finished_worker.tester.keywords['url']},{finished_worker.time_delta_int},\"{finished_worker.time_delta_str}\"\n")
						log.flush()

					if "pytest" in sys.modules:
						break

			while any([worker.good_exit is None for worker in workers]):
				time.sleep(0.025)

			for worker in workers:
				if not worker.good_exit:
					log.write(f"{time.time()},{worker.tester.keywords['url']},{worker.time_delta_int},\"{worker.time_delta_str}\"\n")
					log.flush()
	elif args.mirror:
		_error = None
		_error_code = -1
		try:
			MirrorTester(tier=args.tier, url=args.mirror, tier_0=tier_0).valid
		except urllib.error.HTTPError as error:
			_error = error
			_error_code = error.code
		except urllib.error.URLError as error:
			_error = error
			_error_code = -1

		if _error:
			print(f"""
				Hi!

				Your mirror {args.mirror} returns {_error_code} and has therefor been marked as inactive.
				Please correct this and get back to us if you wish to re-activate the mirror.

				Best regards,
				//Arch Linux mirror team
			""".replace('\t', ''))
			if configuration.email:  # pragma: no cover
				mailto(
					"",
					"",
					"mirrors@archlinux.org",
					None,
					f"Arch Linux mirror {args.mirror} is out of date",
					f"""Hi!

					Your mirror {args.mirror} returns {_error_code}.
					Please correct this and notify us.

					The mirror has been marked as inactive for now.

					//Arch Linux mirror admins""".replace('\t', '')
				)
	elif args.parse:
		con = sqlite3.connect("results.db")
		cur = con.cursor()

		cur.execute("""
			CREATE TABLE IF NOT EXISTS results(
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				unix_time UNIXEPOCH,
				url VARCHAR(255),
				seconds INT,
				message VARCHAR(255),
				UNIQUE(unix_time, url)
			)""")

		for log_file in glob.glob('./*.log'):
			with open(log_file, newline='') as csvfile:
				spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
				for row in spamreader:
					try:
						unix_timestamp, url, seconds, message = row
					except ValueError as err:
						if str(err).startswith('too many values to unpack') or str(err).startswith('not enough values to unpack'):
							continue
						else:  # pragma: no cover
							raise err

					cur.execute("""
						INSERT INTO results (
							unix_time, url, seconds, message
						) VALUES (
							?, ?, ?, ?
						) ON CONFLICT DO NOTHING
					""", (unix_timestamp, url, seconds, message))

		con.commit()
		cur.close()
		con.close()
	elif args.stats:
		con = sqlite3.connect("results.db")
		con.row_factory = sqlite3.Row
		cur = con.cursor()

		problematic_mirrors = {}
		erroneous_mirrors = {}
		rows = cur.execute("""SELECT * FROM results WHERE DATETIME(ROUND(unix_time), 'unixepoch') >= DATETIME('now', '-10 days') ORDER BY url;""")
		for row in rows.fetchall():
			if not row['url'] in problematic_mirrors:
				problematic_mirrors[row['url']] = {
					'hits' : 0,
					'proof' : [],
					'oldest' : None,
					'newest' : None
				}

			problematic_mirrors[row['url']]['hits'] += 1
			problematic_mirrors[row['url']]['proof'].append(dict(row))

			if problematic_mirrors[row['url']]['oldest'] is None or row['unix_time'] < problematic_mirrors[row['url']]['oldest']:
				problematic_mirrors[row['url']]['oldest'] = row['unix_time']
			if problematic_mirrors[row['url']]['newest'] is None or row['unix_time'] > problematic_mirrors[row['url']]['newest']:
				problematic_mirrors[row['url']]['newest'] = row['unix_time']

			if problematic_mirrors[row['url']]['hits'] >= 3:
				erroneous_mirrors[row['url']] = True

		cur.close()
		con.close()

		for url in erroneous_mirrors:
			newest = datetime.datetime.fromtimestamp(problematic_mirrors[url]['newest']).date()
			oldest = datetime.datetime.fromtimestamp(problematic_mirrors[url]['oldest']).date()
			print(f"Between {oldest} - {newest}: {problematic_mirrors[url]['hits']} errors on {url}")
			if args.verbose:
				for error in problematic_mirrors[url]['proof']:
					print(f"\t{error['message']}")
		

	# Upon exiting, store the given configuration used
	config = pathlib.Path('~/.config/mirrortester/config.json').expanduser()
	if config.parent.exists() is False:  # pragma: no cover
		config.parent.mkdir(mode=0o770, parents=True)

	if config.parent.exists():
		with config.open('w') as fh:
			json.dump(dataclasses.asdict(configuration), fh)


if __name__ == '__main__':  # pragma: no cover
	run()
