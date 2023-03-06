import dataclasses
import argparse
import pathlib
import json
import urllib.error

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
	try:
		good_exit = MirrorTester(tier=args.tier, url=args.mirror, tier_0=Tier0(url=args.tier0)).valid
	except urllib.error.HTTPError as error:
		good_exit = False
		print(f"""
			Hi!

			Your mirror {args.mirror} returns {error.code} and has therefor been marked as inactive.
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

				Your mirror {args.mirror} returns {error.code}.
				Please correct this and notify us.

				The mirror has been marked as inactive for now.

				//Arch Linux mirror admins""".replace('\t', '')
			)

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
