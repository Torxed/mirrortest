import dataclasses
import argparse
import pathlib
import json

from ..models import (
	MirrorTester,
	Tier0
)

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
args, unknown = main_options.parse_known_args()


def run() -> None:
	good_exit = MirrorTester(tier=args.tier, url=args.mirror, tier_0=Tier0(url=args.tier0)).valid

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
