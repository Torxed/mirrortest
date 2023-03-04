import urllib.request
import datetime
import pydantic
import typing


@pydantic.dataclasses.dataclass
class Configuration():
	# Some sane default values (in case no config.json was found)
	MAX_TIER1_SYNC_DRIFT_SEC :int = 3600 * 2  # 2h
	MAX_TIER2_SYNC_DRIFT_SEC :int = 3600 * 6  # 6h
	DEFAULT_TIER_NR :int = 2  # Which is the default tier to assume without giving --tier
	USERNAME :str | None = None
	PASSWORD :str | None = None


class Mirror(pydantic.BaseModel):
	"""
	The general structure of all values mirrors need
	"""
	url :pydantic.AnyUrl
	last_sync :datetime.datetime | None = None
	last_update :datetime.datetime | None = None
	arch :str = 'x86_64'

	@pydantic.validator('url', pre=True)
	def validate_url(cls, url :str) -> str:
		if not url.startswith('http'):
			url = f"https://{url}"

		if url[-1] == '/':
			url = url[:-1]

		return url


class Tier0(Mirror):
	@pydantic.root_validator
	def update_times(cls, values :typing.Dict[str, typing.Union[str, datetime.datetime]]) -> typing.Dict[str, typing.Union[str, datetime.datetime]]:
		"""
		At this stage, the class is not instanciated.
		So we will update the dictionary of values before being set
		as class properties (pydantic quirk).
		"""
		values['last_sync'] = datetime.datetime.fromtimestamp(int(Tier0.request(str(values['url']), '/lastsync').strip()))
		values['last_update'] = datetime.datetime.fromtimestamp(int(Tier0.request(str(values['url']), '/lastupdate').strip()))

		return values

	@staticmethod
	def request(url :str, path :str) -> bytes:
		from .session import configuration

		"""
		We can re-work this in the future, but to keep it copy-paste friendly
		from the https://archlinux.org/devel/tier0mirror/ page this is what we need to do.
		"""
		USERNAME, password = url[8:].split(':', 1)
		PASSWORD, domain = password.split('@', 1)
		DOMAIN, _ = domain.split('/', 1)

		configuration.USERNAME = USERNAME
		configuration.PASSWORD = PASSWORD

		request_url = f'{url[:5]}://{DOMAIN}{path}'

		password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
		password_mgr.add_password(None, request_url, USERNAME, PASSWORD)
		handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
		opener = urllib.request.build_opener(handler)
		opener.addheaders = [('User-agent', 'Python/3.10')]
		urllib.request.install_opener(opener)

		req = urllib.request.Request(request_url)
		resp = urllib.request.urlopen(req)
		contents = resp.read()

		return bytes(contents)

	def get_db(self, repo :str) -> bytes:
		"""
		Returns a given gzipped database from this mirror
		"""
		return Tier0.request(self.url, f'/{repo}/os/{self.arch}/{repo}.db.tar.gz')


class MirrorTester(Mirror):
	tier :int
	tier_0 :Tier0

	@pydantic.root_validator
	def update_times(cls, values :typing.Dict[str, typing.Union[str, datetime.datetime]]) -> typing.Dict[str, typing.Union[str, datetime.datetime]]:
		"""
		At this stage, the class is not instanciated.
		So we will update the dictionary of values before being set
		as class properties (pydantic quirk).
		"""
		values['last_sync'] = datetime.datetime.fromtimestamp(int(MirrorTester.request(str(values['url']), '/lastsync').strip()))
		values['last_update'] = datetime.datetime.fromtimestamp(int(MirrorTester.request(str(values['url']), '/lastupdate').strip()))

		return values

	@staticmethod
	def request(url :str, path :str) -> bytes:
		if path[0] == '/':
			path = path[1:]

		response = urllib.request.urlopen(f"{url}/{path}")
		data = response.read()

		return bytes(data)

	def get_db(self, repo :str) -> bytes:
		return MirrorTester.request(self.url, f'/{repo}/os/{self.arch}/{repo}.db.tar.gz')

	@property
	def valid(self) -> bool:
		from .session import configuration

		if (tier0_sync := self.tier_0.last_sync) is None or (self_sync := self.last_sync) is None:
			print(f"Could not get Tier0 sync ({tier0_sync is None}) or mirror did not accept sync ({self_sync is None})")
			return False

		last_sync_delta = tier0_sync - self_sync
		if self.tier == 2 and last_sync_delta.total_seconds() > configuration.MAX_TIER2_SYNC_DRIFT_SEC:
			print(f"{self.url} is out of sync by {last_sync_delta}")
			return False

		if self.tier == 1 and last_sync_delta.total_seconds() > configuration.MAX_TIER1_SYNC_DRIFT_SEC:
			print(f"{self.url} is out of sync {last_sync_delta}")
			return False

		return False
