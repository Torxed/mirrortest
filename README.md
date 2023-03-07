# mirrortest
Test a given Arch Linux mirror against the Tier0 mirror

[![flake8 linting](https://github.com/Torxed/mirrortest/actions/workflows/flake8.yaml/badge.svg)](https://github.com/Torxed/mirrortest/actions/workflows/flake8.yaml)<br>
[![mypy type checking](https://github.com/Torxed/mirrortest/actions/workflows/mypy.yaml/badge.svg)](https://github.com/Torxed/mirrortest/actions/workflows/mypy.yaml)<br>
[![pytest test validation](https://github.com/Torxed/mirrortest/actions/workflows/pytest.yaml/badge.svg)](https://github.com/Torxed/mirrortest/actions/workflows/pytest.yaml)

# Installing

```bash
$ pip install .
```

This project depends only on pydantic.

# Running
The password is the one-time generated token for the tier0 access you get as a mirror admin. 
```bash
$ python -m mirrortest --tier0 'https://torxed:<password>@repos.archlinux.org/$repo/os/$arch' --mirror 'https://ftp.acc.umu.se/mirror/archlinux/'
````

Once run, it creates a `~/.config/mirrortest/config.json` session.<br>
After which `--tier0` is no longer a required parameter.

Keep in mind that your password is stored in plain text in the session config.

# Default values

```python
MAX_TIER1_SYNC_DRIFT_SEC :int = 3600 * 2  # 2h
MAX_TIER2_SYNC_DRIFT_SEC :int = 3600 * 6  # 6h
CON_TIMEOUT :int = 5 # A reasonable HTTP connection timeout limit
DEFAULT_TIER_NR :int = 2  # Which is the default tier to assume without giving --tier
```

# Development

If you wish to run it directly as you edit the source code, you can `cd` into the cloned directory and run 
```bash 
python -m mirrortest --mirror '<mirror url>'
```
