import pathlib
import json
import os

from .models import Configuration

# Initiate configuration with default values
configuration = Configuration()

# Update configuration with stored JSON values (if any)
if (config := pathlib.Path('~/.config/mirrortester/config.json').expanduser()).exists():  # pragma: no cover
	with config.open() as fh:
		json_config = json.load(fh)

	[setattr(configuration, key, val) for key, val in json_config.items()]  # type: ignore

# Update configuration from environment variables (if any)
[setattr(configuration, key, val) for key, val in os.environ.items()]  # type: ignore
