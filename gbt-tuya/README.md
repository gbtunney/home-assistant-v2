# @gbt/tuya-device 🐌

![License: MIT](https://img.shields.io/npm/l/gbt-boilerplate)
![code style: prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg?style=flat-square)

Tuya Cloud device helper (Python CLI).

- List devices and datapoints
- Pretty-print API/MQTT payloads
- Merge “shadow” properties into status
- Filter/inspect specific datapoints
- Listen for live updates via MQTT
- Inspect/execute and monitor scenes
- Quick “connect” sanity check

---

![https://www.home-assistant.io](https://img.shields.io/badge/homeassistant-blue.svg)

### Repository

- Github: [`gbt-monorepo`](https://github.com/gbtunney/gbt-monorepo.git)

## Requirements

- Python 3.9+ (on Catalina use Homebrew: `brew install python`)
- Virtualenv in this folder: `.venv`
- Dependencies (requirements.txt)
  - python-dotenv
  - tuya-iot-py-sdk
  - paho-mqtt==1.6.1 (recommended; 2.x may break tuya-iot 0.6.x)

## Setup

Create venv and install:

```bash
cd /Users/gilliantunney/gbt-monorepo/api/gbt-tuya-device
python3 -m venv .venv
./.venv/bin/python -m pip install -U pip
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pip install "paho-mqtt==1.6.1"
chmod +x ./script.py
```

Home Assistant (server):

```bash
cd /config/api/gbt-tuya-device
python3 -m venv .venv
/config/api/gbt-tuya-device/.venv/bin/python -m pip install -U pip
/config/api/gbt-tuya-device/.venv/bin/python -m pip install -r requirements.txt
/config/api/gbt-tuya-device/.venv/bin/python -m pip install "paho-mqtt==1.6.1"
chmod +x ./script.py
```

.env next to the script:

```env
TUYA_ENDPOINT=https://openapi.tuyaus.com
TUYA_ACCESS_ID=xxxxxxxxxxxxxxxx
TUYA_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
TUYA_USERNAME=you@example.com
TUYA_PASSWORD=your-password
TUYA_COUNTRY_CODE=1
TUYA_APP=smartlife
# Optional defaults
TUYA_DEVICE_ID=ebxxxxxxxxxxxxxxxxxxxx
TUYA_HOME_ID=1234567
```

The script has a portable header that runs the local `.venv/bin/python`.

## Usage

Global flags must come before the subcommand.

```bash
./script.py --pretty < subcommand > [options]
# or with the venv explicitly
./.venv/bin/python ./script.py --pretty < subcommand > [options]
```

If no subcommand is given, the script runs connect (env trace + login) by
default.

### Subcommands

- connect (alias: test): trace env, login, basic checks
  - --device <id>, --verbose
- list: list devices (and optionally datapoints)
  - --dps, --codes <a,b,c>, --raw
- specs: show device spec
  - --device <id>
- get: get device status (shadow merged by default)
  - --device <id>, --codes <a,b,c>, --no-shadow
- dp: get a single datapoint
  - --device <id>, --code <dp_code>, --no-shadow, --value-only
- set: send a single command to a device
  - --device <id>, --code <dp_code>, --value <value>
- listen: live MQTT updates
  - --device <id>, --codes <a,b,c>, --raw, --timeout <s>, --force-exit
- shadow: raw v2 shadow properties
  - --device <id>
- scenes: list/execute/monitor scenes
  - --home <homeId>, --run <sceneId>, --monitor <sceneId>, --interval <s>,
    --timeout <s>

## Examples

Connection sanity check:

```bash
./script.py --pretty connect
./script.py --pretty connect --device ebxxxxxxxx
```

Devices and datapoints:

```bash
./script.py --pretty list
./script.py --pretty list --dps
./script.py --pretty list --dps --codes smoke_sensor_state,battery_percentage
./script.py --pretty list --dps --raw
```

Inspect one device:

```bash
./script.py --pretty specs --device ebxxxxxxxx
./script.py --pretty get --device ebxxxxxxxx
./script.py --pretty get --device ebxxxxxxxx --codes co_state,co_value --no-shadow
./script.py dp --device ebxxxxxxxx --code smoke_sensor_state --value-only
```

Listen for changes:

```bash
./script.py --pretty listen --device ebxxxxxxxx --codes smoke_sensor_state,battery_percentage
./script.py --pretty listen --device ebxxxxxxxx --raw --timeout 60
```

Shadow and scenes:

```bash
./script.py --pretty shadow --device ebxxxxxxxx
./script.py --pretty scenes
./script.py --pretty scenes --run <SCENE_ID>
./script.py --pretty scenes --monitor <SCENE_ID> --interval 3 --timeout 60
```

## Notes

- Shadow merge: get/get_status_any merges v2 “shadow” props if some DPs (e.g.,
  co_state/co_value) are missing in status.
- Pretty output: add --pretty before the subcommand.
- MQTT compatibility: paho-mqtt 1.6.1 is recommended.
- Clean shutdown: Ctrl+C should stop; use listen --timeout or --force-exit if
  needed.
- Home Assistant: you can also run via
  `/config/.venv/bin/python /config/api/gbt-tuya-device/script.py ...`.

## Troubleshooting

- unrecognized arguments: --pretty → Place --pretty before the subcommand.
- No CO datapoints → Try shadow: `shadow` command or `get` without
  `--no-shadow`.
- Bad interpreter / Python missing → Run with `./.venv/bin/python`.

## NPM script

From this folder (uses the local venv’s Python):

```bash
pnpm run run
# package.json: "run": "pnpm exec ./.venv/bin/python ./script.py"
```

## TODO

- [ ] More tests and examples

## Helpful Links

- Tuya IoT Developers Console:
  https://platform.tuya.com/cloud/?id=p1709788991869jakf5p
