import urllib.request
import datetime
import pydantic


@pydantic.dataclasses.dataclass
class Configuration():
	# Some sane default values (in case no config.json was found)
	MAX_TIER1_SYNC_DRIFT_SEC :int = 3600 * 2  # 2h
	MAX_TIER2_SYNC_DRIFT_SEC :int = 3600 * 6  # 6h
	CON_TIMEOUT :int = 5
	DEFAULT_TIER_NR :int = 2  # Which is the default tier to assume without giving --tier
	USERNAME :str | None = None
	PASSWORD :str | None = None
	email :bool = False


class Mirror(pydantic.BaseModel):
	"""
	The general structure of all values mirrors need
	"""
	url :pydantic.AnyUrl
	last_sync :datetime.datetime | None = None
	last_update :datetime.datetime | None = None
	arch :str = 'x86_64'

	@pydantic.validator('url', pre=True)
	def validate_url(cls, url):
		if not url.startswith('http'):  # pragma: no cover
			url = f"https://{url}"

		if url[-1] == '/':  # pragma: no cover
			url = url[:-1]

		return url


class Tier0(Mirror):
	@pydantic.root_validator
	def update_times(cls, values):
		"""
		At this stage, the class is not instanciated.
		So we will update the dictionary of values before being set
		as class properties (pydantic quirk).
		"""
		values['last_sync'] = datetime.datetime.fromtimestamp(int(Tier0.request(str(values['url']), '/lastsync').strip()))
		values['last_update'] = datetime.datetime.fromtimestamp(int(Tier0.request(str(values['url']), '/lastupdate').strip()))

		return values

	@staticmethod
	def request(url, path):  # pragma: no cover
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
		resp = urllib.request.urlopen(req, timeout=configuration.CON_TIMEOUT)
		contents = resp.read()

		return bytes(contents)

	def get_db(self, repo):
		"""
		Returns a given gzipped database from this mirror
		"""
		return Tier0.request(self.url, f'/{repo}/os/{self.arch}/{repo}.db.tar.gz')

	def refresh(self):
		self.last_update = datetime.datetime.fromtimestamp(int(Tier0.request(str(self.url), '/lastupdate').strip()))
		self.last_sync = datetime.datetime.fromtimestamp(int(Tier0.request(str(self.url), '/lastsync').strip()))


class MirrorTester(Mirror):
	tier :int
	tier_0 :Tier0

	@pydantic.root_validator
	def update_times(cls, values):
		"""
		At this stage, the class is not instanciated.
		So we will update the dictionary of values before being set
		as class properties (pydantic quirk).
		"""
		if last_sync_request := MirrorTester.request(str(values['url']), '/lastsync').strip():
			values['last_sync'] = datetime.datetime.fromtimestamp(int(last_sync_request))
		if last_update_request := MirrorTester.request(str(values['url']), '/lastupdate').strip():
			values['last_update'] = datetime.datetime.fromtimestamp(int(last_update_request))

		return values

	@staticmethod
	def request(url, path):
		from .session import configuration

		if path[0] == '/':  # pragma: no cover
			path = path[1:]

		response = urllib.request.urlopen(f"{url}/{path}", timeout=configuration.CON_TIMEOUT)
		data = response.read()

		return bytes(data)

	def get_db(self, repo):
		return MirrorTester.request(self.url, f'/{repo}/os/{self.arch}/{repo}.db.tar.gz')

	@property
	def valid(self):
		from .session import configuration
		from .mailhandle import mailto

		if (tier0_sync := self.tier_0.last_sync) is None or (self_sync := self.last_sync) is None:  # pragma: no cover
			if tier0_sync is None:
				print("Critical! Could not get Tier0 sync.")
			elif self_sync is None:
				print(f"{self.url} does not appear to have a lastsync available.")
			return False

		if (tier0_update := self.tier_0.last_update) is None or (self_update := self.last_update) is None:  # pragma: no cover
			if tier0_update is None:
				print("Critical! Could not get Tier0 sync.")
			elif self_update is None:
				print(f"{self.url} does not appear to have a lastupdate available.")
			return False

		last_update_delta = tier0_update - self_update
		if self.tier == 2 and last_update_delta.total_seconds() > configuration.MAX_TIER2_SYNC_DRIFT_SEC:  # pragma: no cover
			print(f"{self.url} is not updated in {last_update_delta}")
			if configuration.email:
				mailto(
					"",
					"",
					"mirrors@archlinux.org",
					None,
					f"Arch Linux mirror {self.url} is out of date",
					f"""Hi!

					Mirror {self.url} is out of date for {last_update_delta}.
					Please correct this and notify us.

					The mirror has been marked as inactive for now.

					//Arch Linux mirror admins""".replace('\t', '')
				)
			return False

		if self.tier == 1 and last_update_delta.total_seconds() > configuration.MAX_TIER1_SYNC_DRIFT_SEC:  # pragma: no cover
			print(f"{self.url} is not updated in {last_update_delta}")
			if configuration.email:
				mailto(
					"",
					"",
					"mirrors@archlinux.org",
					None,
					f"Arch Linux mirror {self.url} is out of date",
					f"""Hi!

					Mirror {self.url} is out of date for {last_update_delta}.
					Please correct this and notify us.

					The mirror has been marked as inactive for now.

					//Arch Linux mirror admins""".replace('\t', '')
				)
			return False

		last_sync_delta = tier0_sync - self_sync
		if self.tier == 2 and last_sync_delta.total_seconds() > configuration.MAX_TIER2_SYNC_DRIFT_SEC:  # pragma: no cover
			print(f"{self.url} is out of sync by {last_sync_delta}")
			return False

		if self.tier == 1 and last_sync_delta.total_seconds() > configuration.MAX_TIER1_SYNC_DRIFT_SEC:  # pragma: no cover
			print(f"{self.url} is out of sync {last_sync_delta}")
			return False

		return True
