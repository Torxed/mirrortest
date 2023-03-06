import dataclasses
import argparse
import pathlib
import json
import time
import urllib.error
import urllib.request

from ..models import (
	MirrorTester,
	Tier0
)

from ..mailhandle import mailto
from ..session import configuration

# Parse script arguments and use defaults from configuration where needed
main_options = argparse.ArgumentParser(description="Test the health of a given mirror.", add_help=True)
main_options.add_argument(
	"--tier",
	type=int,
	default=configuration.DEFAULT_TIER_NR,
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
args, unknown = main_options.parse_known_args()
configuration.email = args.mail


def run() -> None:
	tier_0 = Tier0(url=args.tier0)

	if args.mirror != '*':
		_error :urllib.error.URLError | urllib.error.HTTPError | None = None
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

					try:
						mirror = MirrorTester(tier=2, url=url, tier_0=tier_0)
						good_exit = mirror.valid
						time_delta_str = tier_0.last_update - mirror.last_update  # type: ignore
						time_delta_int = time_delta_str.total_seconds()
					except urllib.error.HTTPError as error:
						good_exit = False
						time_delta_str = str(error)
						time_delta_int = -1
					except urllib.error.URLError as error:
						good_exit = False
						time_delta_str = str(error)
						time_delta_int = -2
					except TimeoutError as error:
						good_exit = False
						time_delta_str = str(error)
						time_delta_int = -3

					if not good_exit:
						log.write(f"{url},{time_delta_int},\"{time_delta_str}\"\n")
						log.flush()

	# Upon exiting, store the given configuration used
	config = pathlib.Path('~/.config/mirrortester/config.json').expanduser()
	if config.parent.exists() is False:
		config.parent.mkdir(mode=0o770)

	with config.open('w') as fh:
		json.dump(dataclasses.asdict(configuration), fh)

	# Signal to the caller our run
	exit(0 if good_exit else 1)


if __name__ == '__main__':
	run()
