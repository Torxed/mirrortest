import pydantic
import typing
import datetime


class Configuration():
	MAX_TIER1_SYNC_DRIFT_SEC :int = 3600 * 2
	MAX_TIER2_SYNC_DRIFT_SEC :int = 3600 * 6
	CON_TIMEOUT :int = 5
	DEFAULT_TIER_NR :int = 2
	USERNAME :str | None = None
	PASSWORD :str | None = None
	email :bool = False


class Mirror(pydantic.BaseModel):
	url :pydantic.AnyUrl
	last_sync :datetime.datetime | None = None
	last_update :datetime.datetime | None = None
	arch :str = 'x86_64'
	def validate_url(cls, url :str) -> str: ...


class Tier0(Mirror):
	def update_times(cls, values :typing.Dict[str, typing.Union[str, datetime.datetime]]) -> typing.Dict[str, typing.Union[str, datetime.datetime]]: ...

	@staticmethod
	def request(url :str, path :str) -> bytes: ...

	def get_db(self, repo :str) -> bytes: ...

	def refresh(self) -> None: ...


class MirrorTester(Mirror):
	tier :int
	tier_0 :Tier0

	def update_times(cls, values :typing.Dict[str, typing.Union[str, datetime.datetime]]) -> typing.Dict[str, typing.Union[str, datetime.datetime]]: ...

	@staticmethod
	def request(url :str, path :str) -> bytes: ...

	def get_db(self, repo :str) -> bytes: ...

	@property
	def valid(self) -> bool: ...
