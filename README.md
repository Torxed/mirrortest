# mirrortest
Test a given Arch Linux mirror against the Tier0 mirror

# Installing

```bash
$ pip install .
```

This project depends only on pydantic.

# Running

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
```