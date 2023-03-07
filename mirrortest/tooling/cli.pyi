import threading
import datetime
import functools
import argparse

from ..models import MirrorTester

args :argparse.Namespace


class MirrorTesterThreading(threading.Thread):
	tester :functools.partial[MirrorTester]
	mirror_tester :MirrorTester | None = None
	good_exit : bool | None = None
	time_delta_str : datetime.timedelta | str | None = None
	time_delta_int : float | None = None

	def __init__(self, frozen_mirror :functools.partial[MirrorTester]): ...

	def run(self) -> None: ...


def run() -> None: ...
