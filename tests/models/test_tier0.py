import pytest
import datetime

def test_tier0():
	from mirrortest.models import Tier0, MirrorTester

	# Just a patch to remove the need for authentication
	Tier0.request = MirrorTester.request

	mirror = Tier0(url="https://mirror.pseudoform.org/")
	assert mirror.last_sync is not None
	assert mirror.last_update is not None

	assert type(mirror.last_update - datetime.datetime.now()) == datetime.timedelta

	assert type(mirror.get_db('core')) == bytes

	mirror.refresh()