import pytest
import datetime

def test_mirror_tester():
	from mirrortest.models import Tier0, MirrorTester

	# Just a patch to remove the need for authentication
	Tier0.request = MirrorTester.request

	mirror_tier0 = Tier0(url="https://mirror.pseudoform.org/")
	mirror_tier2 = MirrorTester(url="https://mirror.pseudoform.org/", tier=2, tier_0=mirror_tier0)

	assert type(mirror_tier2.tier_0 == Tier0)
	assert type((core_data := mirror_tier2.get_db('core'))) == bytes and len(core_data)
	assert mirror_tier2.valid == True

	mirror_tier1 = MirrorTester(url="https://mirror.pseudoform.org/", tier=1, tier_0=mirror_tier0)

	assert type(mirror_tier1.tier_0 == Tier0)
	assert type((core_data := mirror_tier1.get_db('core'))) == bytes and len(core_data)
	assert mirror_tier1.valid == True