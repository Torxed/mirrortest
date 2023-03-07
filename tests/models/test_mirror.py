import pytest

def test_mirror():
	from mirrortest.models import Mirror

	mirror = Mirror(url="https://mirror.pseudoform.org/")
	assert mirror.last_sync is None
	assert mirror.last_update is None