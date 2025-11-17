#!/usr/bin/env bash
"""exec' "$(cd "$(dirname "$0")" && pwd)/.venv/bin/python" "$0" "$@" # """
import os, sys, time, json, argparse, logging, threading, signal, atexit
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from tuya_iot import (
    TuyaOpenAPI,
    TuyaOpenMQ,
    TuyaDeviceManager,
    TuyaHomeManager,
    TuyaDeviceListener,
    TUYA_LOGGER,
)

# Load .env next to this file
env_path = os.path.join(os.path.dirname(__file__), "secrets.env")
load_dotenv(env_path)

ENDPOINT = os.getenv("TUYA_ENDPOINT", "https://openapi.tuyaus.com")
ACCESS_ID = os.getenv("TUYA_ACCESS_ID")
ACCESS_KEY = os.getenv("TUYA_ACCESS_KEY")
USERNAME = os.getenv("TUYA_USERNAME")
PASSWORD = os.getenv("TUYA_PASSWORD")
COUNTRY_CODE = os.getenv("TUYA_COUNTRY_CODE", "1")
APP = os.getenv("TUYA_APP", "smartlife")
ENV_DEVICE_ID = os.getenv("TUYA_DEVICE_ID")

if not all([ACCESS_ID, ACCESS_KEY, USERNAME, PASSWORD]):
    raise SystemExit(
        "Missing .env values: TUYA_ACCESS_ID, TUYA_ACCESS_KEY, TUYA_USERNAME, TUYA_PASSWORD"
    )

# Pretty-print control (set in main from --pretty)
PRETTY = False


def pp(obj, prefix: str = ""):
    """Pretty-print JSON/dicts when --pretty is enabled."""
    if not PRETTY:
        if isinstance(obj, (dict, list)):
            print(prefix + json.dumps(obj, ensure_ascii=False))
        else:
            print(prefix + str(obj))
        return
    try:
        print(prefix + json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))
    except TypeError:
        try:
            print(
                prefix
                + json.dumps(
                    json.loads(str(obj)), indent=2, sort_keys=True, ensure_ascii=False
                )
            )
        except Exception:
            print(prefix + str(obj))


def _mask(val: str, keep: int = 4) -> str:
    if not val:
        return ""
    s = str(val)
    if len(s) <= keep:
        return "*" * len(s)
    return s[:keep] + "*" * (len(s) - keep)


def trace_env():
    info = {
        "env_file": env_path,
        "env_file_exists": os.path.exists(env_path),
        "endpoint": ENDPOINT,
        "access_id": _mask(ACCESS_ID),
        "access_key": _mask(ACCESS_KEY),
        "username": _mask(USERNAME),
        "country_code": COUNTRY_CODE,
        "app": APP,
        "default_device_id": ENV_DEVICE_ID or None,
    }
    pp(info)


# Logging
TUYA_LOGGER.setLevel(logging.INFO)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

# --- SDK init/login ---
print(f"Python: {sys.executable}")
print(f"Connecting to {ENDPOINT} as {USERNAME} (cc={COUNTRY_CODE}, app={APP})")
openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_KEY)
connect_result = openapi.connect(USERNAME, PASSWORD, COUNTRY_CODE, APP)
print(f"connect_result: {connect_result}")

ti = getattr(openapi, "token_info", None)
if not ti or not getattr(ti, "uid", None):
    raise SystemExit(
        "Login failed (no token/uid). Check endpoint region, app, country code, and Cloud project linking/permissions."
    )

openmq = TuyaOpenMQ(openapi)
device_manager = TuyaDeviceManager(openapi, openmq)
home_manager = TuyaHomeManager(openapi, openmq, device_manager)
try:
    home_manager.update_device_cache()
except Exception as e:
    print(f"update_device_cache failed: {e}")


def test_connection(device_id: Optional[str] = None, verbose: bool = False):
    print("Tracing Tuya environment...")
    trace_env()
    print("Attempting API login/connect...")
    try:
        res = openapi.connect(USERNAME, PASSWORD, COUNTRY_CODE, APP)
    except Exception as e:
        pp({"connect_error": str(e)})
        return
    pp({"connect_result": res})
    ti = getattr(openapi, "token_info", None)
    pp(
        {
            "token_info": {
                "uid": getattr(ti, "uid", None),
                "expire_time": getattr(ti, "expire_time", None),
                "access_token_present": bool(getattr(ti, "access_token", None)),
            }
        }
    )
    # Basic API probes
    uid = getattr(ti, "uid", None)
    if uid:
        homes = openapi.get(f"/v1.0/users/{uid}/homes") or {}
        count = len((homes.get("result") or []))
        pp({"homes_count": count})
    try:
        home_manager.update_device_cache()
    except Exception as e:
        print(f"update_device_cache failed: {e}")
    pp({"device_count": len(device_manager.device_map)})

    # Optional device status probe
    did = device_id or ENV_DEVICE_ID
    if did:
        print(f"Fetching status for device {did} (with shadow merge)...")
        st = get_status_any(did)
        pp(st if verbose else _status_list_to_map(st))
    else:
        print("No device id provided. Pass --device to test a specific device.")


def get_specs(device_id: str) -> Dict[str, Any]:
    res = openapi.get(f"/v1.0/devices/{device_id}/specifications")
    return res or {}


def get_status(device_id: str) -> Dict[str, Any]:
    res = openapi.get(f"/v1.0/devices/{device_id}/status")
    return res or {}


def get_shadow_properties(device_id: str) -> Dict[str, Any]:
    """Tuya v2.0 cloud shadow (often includes more DPs like co_state/co_value)."""
    res = openapi.get(f"/v2.0/cloud/thing/{device_id}/shadow/properties")
    return res or {}


def shadow_to_status_list(shadow: Dict[str, Any]):
    """Convert shadow properties -> [{'code':..., 'value':...}, ...]"""
    props = ((shadow or {}).get("result") or {}).get("properties", []) or []
    out = []
    for p in props:
        out.append(
            {"code": p.get("code"), "value": p.get("value"), "time": p.get("time")}
        )
    return out


def get_status_any(device_id: str) -> Dict[str, Any]:
    """Get status; if CO fields missing, merge from shadow."""
    st = get_status(device_id)
    codes = {it.get("code") for it in (st.get("result") or []) if isinstance(it, dict)}
    need_shadow = not ({"co_state", "co_value"} & codes)
    if need_shadow:
        sh = get_shadow_properties(device_id)
        merged = list((st.get("result") or []))
        # Merge/overwrite by code
        seen = {it.get("code") for it in merged if isinstance(it, dict)}
        for it in shadow_to_status_list(sh):
            if it.get("code") not in seen:
                merged.append(it)
        return {"result": merged, "source": "status+shadow"}
    return st


def _status_list_to_map(st):
    items = (st or {}).get("result") or []
    out = {}
    for it in items:
        if isinstance(it, dict) and "code" in it:
            out[it["code"]] = it.get("value")
    return out


def get_dp_values(device_id, codes, use_shadow=True):
    st = get_status_any(device_id) if use_shadow else get_status(device_id)
    cur = _status_list_to_map(st)
    if not codes:
        return cur
    return {c: cur.get(c) for c in codes}


def list_devices(
    with_dps: bool = False, codes: Optional[set] = None, raw: bool = False
):
    print("Known devices:")
    for d in device_manager.device_map.values():
        print(f"- {d.name} | id={d.id} | category={d.category}")
        if not with_dps:
            continue

        specs = get_specs(d.id)
        status = get_status_any(d.id)  # use fallback-aware

        if raw:
            print(f"  Raw specs/status for {d.id}:")
            pp({"specs": specs, "status": status}, prefix="  ")
            continue

        # functions (DP specs)
        funcs = {}
        try:
            for f in (specs.get("result") or {}).get("functions", []):
                vals = f.get("values")
                try:
                    vals_parsed = (
                        json.loads(vals) if isinstance(vals, str) and vals else vals
                    )
                except Exception:
                    vals_parsed = vals
                funcs[f.get("code")] = {"type": f.get("type"), "values": vals_parsed}
        except Exception:
            pass

        # current status -> code -> value
        cur = {}
        try:
            for it in status.get("result") or []:
                if isinstance(it, dict) and "code" in it:
                    cur[it["code"]] = it.get("value")
        except Exception:
            pass

        if codes:
            funcs = {k: v for k, v in funcs.items() if k in codes}
            cur = {k: v for k, v in cur.items() if k in codes}

        print(f"  DP specs/status for {d.id}:")
        pp({"functions": funcs, "status": cur}, prefix="  ")


def coerce_value_for_code(code_def: Optional[Dict[str, Any]], raw: str):
    if not code_def:
        try:
            return json.loads(raw)
        except Exception:
            pass
        if raw.lower() in ("true", "false"):
            return raw.lower() == "true"
        try:
            return int(raw)
        except Exception:
            return raw
    t = (code_def.get("type") or "").lower()
    if t == "boolean":
        return raw.lower() == "true"
    if t == "integer":
        return int(raw)
    if t in ("json", "raw", "string"):
        try:
            return json.loads(raw)
        except Exception:
            return raw
    if t == "enum":
        return raw
    return raw


def find_code_def(specs: Dict[str, Any], code: str) -> Optional[Dict[str, Any]]:
    for item in (specs.get("result") or {}).get("functions", []):
        if item.get("code") == code:
            return item
    return None


def send_command(device_id: str, code: str, value_str: str):
    specs = get_specs(device_id)
    code_def = find_code_def(specs, code)
    if not code_def:
        print(
            f"Warning: code '{code}' not in functions for device {device_id}. This device may be read-only."
        )
    value = coerce_value_for_code(code_def, value_str)
    payload = {"commands": [{"code": code, "value": value}]}
    res = openapi.post(f"/v1.0/devices/{device_id}/commands", payload)
    pp({"request": payload, "response": res})


def print_device(device_id: str):
    print(f"=== {device_id} specs ===")
    s = get_specs(device_id)
    pp(s)
    print(f"=== {device_id} status (with shadow fallback) ===")
    st = get_status_any(device_id)
    pp(st)
    # Highlight common sensor fields if present
    interesting = {}
    for item in st.get("result", []):
        if item.get("code") in (
            "smoke_sensor_state",
            "smoke_sensor_value",
            "gas_sensor_state",
            "co_state",
            "co2_state",
            "co_value",
            "co2_value",
            "battery_state",
            "battery_percentage",
            "alarm_state",
            "silence",
            "muffling",
            "fault",
            "checking_result",
        ):
            interesting[item["code"]] = item.get("value")
    if interesting:
        print(f"Relevant: {interesting}")


class FilteredDeviceListener(TuyaDeviceListener):
    def __init__(self, device_id: Optional[str], codes: Optional[set]):
        self.device_id = device_id
        self.codes = codes

    def _ok(self, d_id: str):
        return (self.device_id is None) or (d_id == self.device_id)

    def _filter_status(self, status: Any):
        if not isinstance(status, dict) or not self.codes:
            return status
        return {k: v for k, v in status.items() if k in self.codes}

    def update_device(self, device):
        if not self._ok(device.id):
            return
        filtered = self._filter_status(getattr(device, "status", {}))
        pp(filtered, prefix=f"[update] {device.name} ({device.id}) -> ")

    def add_device(self, device):
        if not self._ok(device.id):
            return
        print(f"[add] {device.name} ({device.id})")

    def remove_device(self, device_id):
        if not self._ok(device_id):
            return
        print(f"[remove] {device_id}")


def add_raw_mq_listener(
    device_id: Optional[str], codes: Optional[set], raw: bool = False
):
    def on_message(msg):
        # msg may be a JSON string
        try:
            data = json.loads(msg) if isinstance(msg, str) else (msg or {})
        except Exception:
            print(f"[mq] {msg}")
            return
        d_id = data.get("devId") or data.get("device_id")
        if device_id and d_id != device_id:
            return
        if raw:
            pp(data, prefix=f"[mq] {d_id}: ")
            return
        # Summarize status array if present
        status = data.get("status") or data.get("data") or {}
        if isinstance(status, list):
            if codes:
                status = [it for it in status if it.get("code") in codes]
            summary = {
                it.get("code"): it.get("value") for it in status if isinstance(it, dict)
            }
        elif isinstance(status, dict):
            summary = {k: v for k, v in status.items() if (not codes or k in codes)}
        else:
            summary = status
        pp(summary, prefix=f"[mq] {d_id}: ")

    openmq.add_message_listener(on_message)


# Graceful shutdown
STOP = threading.Event()


def _stop_openmq(grace: float = 5.0, force: bool = False):
    mq = globals().get("openmq")
    if not mq:
        return
    try:
        mq.stop()
    except Exception:
        pass
    for attr in ("mqttc", "_mqttc", "mqtt_client", "_mqtt_client"):
        mqttc = getattr(mq, attr, None)
        if mqttc:
            try:
                mqttc.loop_stop()
            except Exception:
                pass
            try:
                mqttc.disconnect()
            except Exception:
                pass
            break
    t = getattr(mq, "_thread", None) or getattr(mq, "thread", None)
    if t:
        try:
            t.join(timeout=grace)
        except Exception:
            pass
    if force:
        os._exit(0)


def _handle_signal(signum, frame):
    STOP.set()
    _stop_openmq(grace=5.0, force=False)


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)
atexit.register(lambda: _stop_openmq(grace=2.0, force=False))


def _get_uid() -> Optional[str]:
    return getattr(getattr(openapi, "token_info", None), "uid", None)


def _get_homes():
    uid = _get_uid()
    if not uid:
        return []
    res = openapi.get(f"/v1.0/users/{uid}/homes")
    return (res or {}).get("result", []) or []


def _get_default_home_id():
    env_home = os.getenv("TUYA_HOME_ID")
    if env_home:
        return env_home
    homes = _get_homes()
    return str(homes[0]["home_id"]) if homes else None


def list_scenes(home_id: Optional[str] = None):
    hid = home_id or _get_default_home_id()
    if not hid:
        print("No home id. Set TUYA_HOME_ID or ensure your account has a Home.")
        return
    res = openapi.get(f"/v1.0/homes/{hid}/scenes")
    scenes = (res or {}).get("result", []) or []
    if not scenes:
        print(f"No scenes found for home {hid}")
        return
    print(f"Scenes for home {hid}:")
    for sc in scenes:
        pp(
            {
                "id": sc.get("id"),
                "name": sc.get("name"),
                "enabled": sc.get("enabled"),
                "last_exec_time": sc.get("last_exec_time") or sc.get("last_executed"),
                "match_type": sc.get("match_type"),
            },
            prefix="  ",
        )


def _find_scene(scene_id: str) -> Optional[dict]:
    # search all homes for the scene id
    for h in _get_homes():
        res = openapi.get(f"/v1.0/homes/{h['home_id']}/scenes")
        for sc in (res or {}).get("result", []) or []:
            if sc.get("id") == scene_id:
                return sc
    return None


def _get_scene_last_exec(scene_id: str) -> Optional[int]:
    sc = _find_scene(scene_id)
    if not sc:
        return None
    val = sc.get("last_exec_time") or sc.get("last_executed")
    try:
        return int(val) if val is not None else None
    except Exception:
        return None


def monitor_scene(scene_id: str, interval: int = 5, timeout: int = 0):
    if not scene_id:
        print("Missing --monitor <scene_id>")
        return
    print(
        f"Monitoring scene {scene_id} (interval={interval}s, timeout={timeout or '∞'}s)..."
    )
    start = time.time()
    prev = _get_scene_last_exec(scene_id)
    pp({"scene_id": scene_id, "initial_last_exec_time": prev})
    while not STOP.wait(interval):
        cur = _get_scene_last_exec(scene_id)
        if cur is not None and cur != prev:
            pp({"scene_id": scene_id, "triggered_at": cur})
            prev = cur
        if timeout and (time.time() - start) >= timeout:
            break


def main():
    parser = argparse.ArgumentParser(
        description="Tuya helper (query, command, listen)."
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )
    sub = parser.add_subparsers(dest="cmd")

    # test/connect (same behavior)
    p_test = sub.add_parser(
        "test", help="Trace env, (re)connect, and run basic API checks"
    )
    p_test.add_argument(
        "--device", default=ENV_DEVICE_ID, help="Optional device id to probe"
    )
    p_test.add_argument(
        "--verbose", action="store_true", help="Print full status JSON for device probe"
    )

    p_connect = sub.add_parser(
        "connect", help="Alias of 'test' (connect/login and sanity checks)"
    )
    p_connect.add_argument(
        "--device", default=ENV_DEVICE_ID, help="Optional device id to probe"
    )
    p_connect.add_argument(
        "--verbose", action="store_true", help="Print full status JSON for device probe"
    )

    p_list = sub.add_parser("list", help="List devices")
    p_list.add_argument(
        "--dps",
        action="store_true",
        help="Also show datapoint specs and current values",
    )
    p_list.add_argument(
        "--codes", default="", help="Filter to these DP codes (comma-separated)"
    )
    p_list.add_argument(
        "--raw",
        action="store_true",
        help="Show raw API JSON for specs/status (use with --dps)",
    )

    p_specs = sub.add_parser("specs", help="Show specs for a device")
    p_specs.add_argument(
        "--device", default=ENV_DEVICE_ID, required=ENV_DEVICE_ID is None
    )

    p_get = sub.add_parser("get", help="Get status for a device")
    p_get.add_argument(
        "--device", default=ENV_DEVICE_ID, required=ENV_DEVICE_ID is None
    )
    p_get.add_argument(
        "--codes", default="", help="Comma-separated DP codes to print (optional)"
    )
    p_get.add_argument(
        "--no-shadow",
        dest="shadow",
        action="store_false",
        help="Do not merge v2 shadow properties",
    )
    p_get.set_defaults(shadow=True)

    p_dp = sub.add_parser("dp", help="Get a specific datapoint value")
    p_dp.add_argument("--device", default=ENV_DEVICE_ID, required=ENV_DEVICE_ID is None)
    p_dp.add_argument(
        "--code", required=True, help="DP code (e.g., smoke_sensor_state)"
    )
    p_dp.add_argument(
        "--no-shadow",
        dest="shadow",
        action="store_false",
        help="Do not merge v2 shadow properties",
    )
    p_dp.add_argument(
        "--value-only",
        action="store_true",
        help="Print only the value (no JSON wrapper)",
    )
    p_dp.set_defaults(shadow=True)

    p_set = sub.add_parser("set", help="Send a single command to a device")
    p_set.add_argument(
        "--device", default=ENV_DEVICE_ID, required=ENV_DEVICE_ID is None
    )
    p_set.add_argument("--code", required=True, help="DP code (e.g., switch_led)")
    p_set.add_argument(
        "--value", required=True, help="Value (bool/int/string or JSON for JSON types)"
    )

    p_listen = sub.add_parser("listen", help="Listen for live updates")
    p_listen.add_argument(
        "--device", default=ENV_DEVICE_ID, help="Filter to a specific device id"
    )
    p_listen.add_argument(
        "--codes", default="", help="Comma-separated DP codes to print (optional)"
    )
    p_listen.add_argument(
        "--raw", action="store_true", help="Print full raw MQTT JSON payload"
    )
    p_listen.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="Auto-stop after N seconds (0 = run forever)",
    )
    p_listen.add_argument(
        "--force-exit", action="store_true", help="Forcefully exit if shutdown hangs"
    )

    p_shadow = sub.add_parser("shadow", help="Show v2.0 shadow properties for a device")
    p_shadow.add_argument(
        "--device", default=ENV_DEVICE_ID, required=ENV_DEVICE_ID is None
    )

    p_scenes = sub.add_parser("scenes", help="List or monitor scenes")
    p_scenes.add_argument(
        "--home", help="Home ID (defaults to TUYA_HOME_ID or first home)"
    )
    p_scenes.add_argument("--run", help="Execute a scene by ID")
    p_scenes.add_argument(
        "--monitor", help="Monitor a scene by ID (poll last_exec_time)"
    )
    p_scenes.add_argument(
        "--interval", type=int, default=5, help="Poll interval seconds (monitor)"
    )
    p_scenes.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="Auto-stop after N seconds (monitor; 0=forever)",
    )

    args = parser.parse_args()

    global PRETTY
    PRETTY = bool(args.pretty)

    # Default: run connect/test when no subcommand given
    if args.cmd is None:
        test_connection(getattr(args, "device", None), verbose=False)
        return

    if args.cmd in ("test", "connect"):
        test_connection(
            getattr(args, "device", None), verbose=getattr(args, "verbose", False)
        )
        return

    if args.cmd == "list":
        code_set = (
            set([c.strip() for c in getattr(args, "codes", "").split(",") if c.strip()])
            if getattr(args, "codes", "")
            else None
        )
        list_devices(
            with_dps=getattr(args, "dps", False),
            codes=code_set,
            raw=getattr(args, "raw", False),
        )
        return

    if args.cmd == "specs":
        print_device(args.device)
        return

    if args.cmd == "get":
        if getattr(args, "codes", ""):
            code_set = [c.strip() for c in args.codes.split(",") if c.strip()]
            vals = get_dp_values(args.device, code_set, use_shadow=args.shadow)
            pp(vals)
        else:
            st = get_status_any(args.device) if args.shadow else get_status(args.device)
            pp(st)
        return

    if args.cmd == "dp":
        vals = get_dp_values(args.device, [args.code], use_shadow=args.shadow)
        val = vals.get(args.code)
        if args.value_only:
            print(val)
        else:
            pp({args.code: val})
        return

    if args.cmd == "set":
        send_command(args.device, args.code, args.value)
        return

    if args.cmd == "listen":
        code_set = (
            set([c.strip() for c in args.codes.split(",") if c.strip()])
            if args.codes
            else None
        )
        device_manager.add_device_listener(
            FilteredDeviceListener(args.device, code_set)
        )
        add_raw_mq_listener(args.device, code_set, raw=args.raw)
        print("Starting Tuya OpenMQ listener...")
        openmq.start()
        try:
            if args.timeout > 0:
                STOP.wait(timeout=args.timeout)
            else:
                while not STOP.wait(1.0):
                    pass
        except KeyboardInterrupt:
            STOP.set()
        finally:
            _stop_openmq(grace=5.0, force=args.force_exit)
        return

    if args.cmd == "shadow":
        sh = get_shadow_properties(args.device)
        pp(sh)
        return

    if args.cmd == "scenes":
        if args.run:
            res = openapi.post(f"/v1.0/scenes/{args.run}/execute", {})
            pp({"execute_result": res})
        if args.monitor:
            monitor_scene(args.monitor, interval=args.interval, timeout=args.timeout)
        else:
            list_scenes(args.home)
        return


if __name__ == "__main__":
    main()
