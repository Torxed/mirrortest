import pydantic
import typing
import datetime


class Configuration():
	MAX_TIER1_SYNC_DRIFT_SEC :int = 3600 * 2  # 2h
	MAX_TIER2_SYNC_DRIFT_SEC :int = 3600 * 6  # 6h
	DEFAULT_TIER_NR :int = 2  # Which is the default tier to assume without giving --tier
	USERNAME :str | None = None
	PASSWORD :str | None = None


class Mirror(pydantic.BaseModel):
	def validate_url(cls, url :str) -> str: ...


class Tier0(Mirror):
	def update_times(cls, values :typing.Dict[str, typing.Union[str, datetime.datetime]]) -> typing.Dict[str, typing.Union[str, datetime.datetime]]: ...

	@staticmethod
	def request(url :str, path :str) -> bytes: ...

	def get_db(self, repo :str) -> bytes: ...


class MirrorTester(Mirror):
	def update_times(cls, values :typing.Dict[str, typing.Union[str, datetime.datetime]]) -> typing.Dict[str, typing.Union[str, datetime.datetime]]: ...

	@staticmethod
	def request(url :str, path :str) -> bytes: ...

	def get_db(self, repo :str) -> bytes: ...

	@property
	def valid(self) -> bool: ...
