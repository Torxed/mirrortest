#!/usr/bin/env python3

'''Utilities for opening files or URLs in the registered default application
and for sending e-mail using the user's preferred composer.

https://stackoverflow.com/a/19779373/3211506

'''

__version__ = '1.1'
__all__ = ['open', 'mailto']

import os
import sys
import webbrowser
import subprocess

from email.utils import encode_rfc2231

_controllers = {}
_open = None

fileopen = open


class BaseController(object):
	'''Base class for open program controllers.'''

	def __init__(self, name):
		self.name = name

	def open(self, filename):
		raise NotImplementedError


class Controller(BaseController):
	'''Controller for a generic open program.'''

	def __init__(self, *args):
		super(Controller, self).__init__(os.path.basename(args[0]))
		self.args = list(args)

	def _invoke(self, cmdline):
		if sys.platform[:3] == 'win':
			closefds = False
			startupinfo = subprocess.STARTUPINFO()
			startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
		else:
			closefds = True
			startupinfo = None

		if (os.environ.get('DISPLAY') or sys.platform[:3] == 'win' or sys.platform == 'darwin'):
			inout = fileopen(os.devnull, 'r+')
		else:
			# for TTY programs, we need stdin/out
			inout = None

		# if possible, put the child precess in separate process group,
		# so keyboard interrupts don't affect child precess as well as
		# Python
		setsid = getattr(os, 'setsid', None)
		if not setsid:
			setsid = getattr(os, 'setpgrp', None)

		pipe = subprocess.Popen(
			cmdline,
			stdin=inout,
			stdout=inout,
			stderr=inout,
			close_fds=closefds,
			preexec_fn=setsid,
			startupinfo=startupinfo
		)

		# It is assumed that this kind of tools (gnome-open, kfmclient,
		# exo-open, xdg-open and open for OSX) immediately exit after lauching
		# the specific application
		returncode = pipe.wait()
		if hasattr(self, 'fixreturncode'):
			returncode = self.fixreturncode(returncode)
		return not returncode

	def open(self, filename):
		if isinstance(filename, str):
			cmdline = self.args + [filename]
		else:
			# assume it is a sequence
			cmdline = self.args + filename
		try:
			return self._invoke(cmdline)
		except OSError:
			return False


# Platform support for Windows
if sys.platform[:3] == 'win':

	class Start(BaseController):
		'''Controller for the win32 start progam through os.startfile.'''

		def open(self, filename):
			try:
				os.startfile(filename)
			except WindowsError:
				# [Error 22] No application is associated with the specified
				# file for this operation: '<URL>'
				return False
			else:
				return True

	_controllers['windows-default'] = Start('start')
	_open = _controllers['windows-default'].open


# Platform support for MacOS
elif sys.platform == 'darwin':
	_controllers['open'] = Controller('open')
	_open = _controllers['open'].open


# Platform support for Unix
else:

	import stat

	# @WARNING: use the private API of the webbrowser module
	# from webbrowser import _iscommand

	def _isexecutable(cmd):
		if os.path.isfile(cmd):
			mode = os.stat(cmd)[stat.ST_MODE]
			if mode & stat.S_IXUSR or mode & stat.S_IXGRP or mode & stat.S_IXOTH:
				return True
		return False

	def _iscommand(cmd):
		"""Return True if cmd is executable or can be found on the executable
		search path."""
		if _isexecutable(cmd):
			return True

		path = os.environ.get("PATH")
		if not path:
			return False
		for d in path.split(os.pathsep):
			exe = os.path.join(d, cmd)
			if _isexecutable(exe):
				return True
		return False

	class KfmClient(Controller):
		'''Controller for the KDE kfmclient program.'''

		def __init__(self, kfmclient='kfmclient'):
			super(KfmClient, self).__init__(kfmclient, 'exec')
			self.kde_version = self.detect_kde_version()

		def detect_kde_version(self):
			kde_version = None
			try:
				info = subprocess.getoutput('kde-config --version')

				for line in info.splitlines():
					if line.startswith('KDE'):
						kde_version = line.split(':')[-1].strip()
						break
			except (OSError, RuntimeError):
				pass

			return kde_version

		def fixreturncode(self, returncode):
			if returncode is not None and self.kde_version > '3.5.4':
				return returncode
			else:
				return os.EX_OK

	def detect_desktop_environment():
		'''Checks for known desktop environments

		Return the desktop environments name, lowercase (kde, gnome, xfce)
		or "generic"

		'''

		desktop_environment = 'generic'

		if os.environ.get('KDE_FULL_SESSION') == 'true':
			desktop_environment = 'kde'
		elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
			desktop_environment = 'gnome'
		else:
			try:
				info = subprocess.getoutput('xprop -root _DT_SAVE_MODE')
				if ' = "xfce4"' in info:
					desktop_environment = 'xfce'
			except (OSError, RuntimeError):
				pass

		return desktop_environment

	def register_X_controllers():
		if _iscommand('kfmclient'):
			_controllers['kde-open'] = KfmClient()

		for command in ('gnome-open', 'exo-open', 'xdg-open'):
			if _iscommand(command):
				_controllers[command] = Controller(command)

	def get():
		controllers_map = {
			'gnome': 'gnome-open',
			'kde': 'kde-open',
			'xfce': 'exo-open',
		}

		desktop_environment = detect_desktop_environment()

		try:
			controller_name = controllers_map[desktop_environment]
			return _controllers[controller_name].open

		except KeyError:
			if 'xdg-open' in _controllers:
				return _controllers['xdg-open'].open
			else:
				return webbrowser.open

	if os.environ.get("DISPLAY"):
		register_X_controllers()
	_open = get()
	print(_open)


def open(filename):
	'''Open a file or an URL in the registered default application.'''

	return _open(filename)


def _fix_addersses(**kwargs):
	for headername in ('address', 'to', 'cc', 'bcc'):
		try:
			headervalue = kwargs[headername]
			if not headervalue:
				del kwargs[headername]
				continue
			elif not isinstance(headervalue, str):
				# assume it is a sequence
				headervalue = ','.join(headervalue)

		except KeyError:
			pass
		except TypeError:
			raise TypeError(
				'string or sequence expected for "%s", '
				'%s found' % (
					headername,
					type(headervalue).__name__
				)
			)
		else:
			translation_map = {'%': '%25', '&': '%26', '?': '%3F'}
			for char, replacement in list(translation_map.items()):
				headervalue = headervalue.replace(char, replacement)
			kwargs[headername] = headervalue

	return kwargs


def mailto_format(**kwargs):
	# @TODO: implement utf8 option

	kwargs = _fix_addersses(**kwargs)
	parts = []
	for headername in ('to', 'cc', 'bcc', 'subject', 'body'):
		if headername in kwargs:
			headervalue = kwargs[headername]
			if not headervalue:
				continue
			if headername in ('address', 'to', 'cc', 'bcc'):
				parts.append('%s=%s' % (headername, headervalue))
			else:
				headervalue = encode_rfc2231(headervalue, charset="utf-8")[7:]  # @TODO: check
				parts.append('%s=%s' % (headername, headervalue))

	mailto_string = 'mailto:%s' % kwargs.get('address', '')
	if parts:
		mailto_string = '%s?%s' % (mailto_string, '&'.join(parts))

	return mailto_string


def mailto(address, to=None, cc=None, bcc=None, subject=None, body=None):
	""" # noqa: E101
	Send an e-mail using the user's preferred composer.

	Open the user's preferred e-mail composer in order to send a mail to
	address(es) that must follow the syntax of RFC822. Multiple addresses
	may be provided (for address, cc and bcc parameters) as separate
	arguments.

	All parameters provided are used to prefill corresponding fields in
	the user's e-mail composer. The user will have the opportunity to
	change any of this information before actually sending the e-mail.

	address - specify the destination recipient
	cc      - specify a recipient to be copied on the e-mail
	bcc     - specify a recipient to be blindly copied on the e-mail
	subject - specify a subject for the e-mail
	body    - specify a body for the e-mail. Since the user will be able
			  to make changes before actually sending the e-mail, this
			  can be used to provide the user with a template for the
			  e-mail text may contain linebreaks
	attach  - specify an attachment for the e-mail. file must point to
			  an existing file (UNSUPPORTED)

	"""

	mailto_string = mailto_format(**locals())
	return open(mailto_string)
