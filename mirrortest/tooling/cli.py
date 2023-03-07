import dataclasses
import argparse
import pathlib
import json
import time
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
				else:
					self.time_delta_int = -5
				self.good_exit = True
			else:
				self.time_delta_str = 'Could not find /lastupdate on mirror'
				self.time_delta_int = -6
		except urllib.error.HTTPError as error:
			self.good_exit = False
			self.time_delta_str = str(error)
			self.time_delta_int = -1
		except urllib.error.URLError as error:
			self.good_exit = False
			self.time_delta_str = str(error)
			self.time_delta_int = -2
		except TimeoutError as error:
			self.good_exit = False
			self.time_delta_str = str(error)
			self.time_delta_int = -3
		except pydantic.error_wrappers.ValidationError as error:
			self.good_exit = False
			self.time_delta_str = str(error)
			self.time_delta_int = -4

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
	required=True,
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
args, unknown = main_options.parse_known_args()
configuration.email = args.mail


def run():
	tier_0 = Tier0(url=args.tier0)

	if args.mirror != '*':
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
			if configuration.email:
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
	else:
		# Retrieve complete mirror list
		response = urllib.request.urlopen("https://archlinux.org/mirrorlist/all/")
		data = response.read()
		workers :list[MirrorTesterThreading] = []

		with open(f'output_{time.time()}.log', 'w') as log:
			for server in data.split(b'\n'):

				if b'#Server = ' not in server:
					continue
				elif len(server.strip()) == 0:
					continue

				if server.startswith(b'#Server'):
					_, url = server.split(b'=', 1)
					url, _ = url.split(b'/$repo', 1)
					url = url.strip().decode()

					while len(workers) >= args.workers and not any([worker.good_exit is not None for worker in workers]):
						time.sleep(0.025)

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

					if not finished_worker.good_exit:
						log.write(f"{finished_worker.tester.keywords['url']},{finished_worker.time_delta_int},\"{finished_worker.time_delta_str}\"\n")
						log.flush()

			while any([worker.good_exit is None for worker in workers]):
				time.sleep(0.025)

			for worker in workers:
				if not worker.good_exit:
					log.write(f"{worker.tester.keywords['url']},{worker.time_delta_int},\"{worker.time_delta_str}\"\n")
					log.flush()

	# Upon exiting, store the given configuration used
	config = pathlib.Path('~/.config/mirrortester/config.json').expanduser()
	if config.parent.exists() is False:
		config.parent.mkdir(mode=0o770)

	with config.open('w') as fh:
		json.dump(dataclasses.asdict(configuration), fh)


if __name__ == '__main__':
	run()
