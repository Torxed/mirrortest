import pytest

def test_configuration():
	from mirrortest.models import Configuration

	default_values = Configuration()
	assert default_values.MAX_TIER1_SYNC_DRIFT_SEC == 3600 * 2
	assert default_values.MAX_TIER2_SYNC_DRIFT_SEC == 3600 * 6
	assert default_values.CON_TIMEOUT == 5
	assert default_values.DEFAULT_TIER_NR == 2
	assert default_values.USERNAME is None
	assert default_values.PASSWORD is None
	assert default_values.email == False

	# Attempt to input bad values, this will work
	# once we swap pydantic.dataclasses.dataclass for
	# pydantic.BaseModel - and then convert it to JSON
	# instance = Configuration()
	# instance.MAX_TIER2_SYNC_DRIFT_SEC = "moo"