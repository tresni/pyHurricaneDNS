# HurricaneDNS

## Requirements
 * python3
 * python-lxml
 * dnspython (optional - for importing BIND zones)

## Install

### Online

```bash
pip install hurricanedns
```

### Offline

```bash
# Get source code
git clone https://github.com/tresni/pyHurricaneDNS

# Build
cd pyHurricaneDNS
python3 setup.py build

# Install using pip
pip install .

# Install using pipx(OS like debian?)
# pipx install .
```

## What works?

- add (domain, record).
  - Support adding DDNS keys while adding new records.

- del (domain, record).
  - Using filter, delete all match records, **please handle with caution**.

- ls (domain, record)
- import (BIND zone files)
- cp (records from one domain to another)

## TODO

- Edit record. *Currently implemented through del+add*.
- Delete record with specified ID.

## Usage

Get the party started by logging in:

```
hurricanedns <he.net username> <he.net password>
```

You'll get dropped to a `hurricanedns` command prompt:

```
[<username>@dns.he.net]
```

Start with `help`.

You can always get specific help for a command by doing `help [command]`, for example `help ls`

To quit, use `exit`, `EOF`, or CTRL-D.
