import json
import shutil
import subprocess
import time

SCHEMA_ID = "snailicide.ha_registry_export.v1"
SCHEMA_VERSION = 1

EXPORTER_PATH = "/config/ha_exporter.sh"
EXPORT_LOCAL_PATH = "/local/ha_exports"
COMMAND_TIMEOUT_SECONDS = 120
OUTPUT_LIMIT = 8000

EXPORT_FILES = {
    "entities": {
        "json": "ha_entities_raw.json",
        "csv": "ha_entities_raw.csv",
    },
    "devices": {
        "json": "ha_devices_raw.json",
        "csv": "ha_devices_raw.csv",
    },
    "areas": {
        "json": "ha_areas_raw.json",
        "csv": "ha_areas_raw.csv",
    },
    "labels": {
        "json": "ha_labels_raw.json",
        "csv": "ha_labels_raw.csv",
    },
    "floors": {
        "json": "ha_floors_raw.json",
        "csv": "ha_floors_raw.csv",
    },
}


def _make_request_id():
    try:
        return "ha-export-%d" % int(time.time() * 1000)
    except Exception:
        return "ha-export-auto"


def _as_request_id(value):
    if value is None:
        return _make_request_id()

    try:
        request_id = str(value).strip()
        if request_id:
            return request_id
    except Exception:
        pass

    return _make_request_id()


@pyscript_compile
def _run_exporter():
    started_at = time.time()
    bash_path = shutil.which("bash")
    jq_path = shutil.which("jq")

    if bash_path is None:
        return {
            "ok": False,
            "returncode": None,
            "duration_seconds": 0,
            "stdout": "",
            "stderr": "bash is not available in the Home Assistant Core environment",
            "exporter_path": EXPORTER_PATH,
            "bash_path": None,
            "jq_path": jq_path,
        }

    if jq_path is None:
        return {
            "ok": False,
            "returncode": None,
            "duration_seconds": 0,
            "stdout": "",
            "stderr": "jq is not available in the Home Assistant Core environment",
            "exporter_path": EXPORTER_PATH,
            "bash_path": bash_path,
            "jq_path": None,
        }

    try:
        completed = subprocess.run(
            [bash_path, EXPORTER_PATH],
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return {
            "ok": False,
            "returncode": None,
            "duration_seconds": round(time.time() - started_at, 3),
            "stdout": (error.stdout or "")[-OUTPUT_LIMIT:],
            "stderr": "Exporter timed out after %s seconds" % COMMAND_TIMEOUT_SECONDS,
            "exporter_path": EXPORTER_PATH,
            "bash_path": bash_path,
            "jq_path": jq_path,
        }
    except Exception as error:
        return {
            "ok": False,
            "returncode": None,
            "duration_seconds": round(time.time() - started_at, 3),
            "stdout": "",
            "stderr": str(error)[-OUTPUT_LIMIT:],
            "exporter_path": EXPORTER_PATH,
            "bash_path": bash_path,
            "jq_path": jq_path,
        }

    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "duration_seconds": round(time.time() - started_at, 3),
        "stdout": (completed.stdout or "")[-OUTPUT_LIMIT:],
        "stderr": (completed.stderr or "")[-OUTPUT_LIMIT:],
        "exporter_path": EXPORTER_PATH,
        "bash_path": bash_path,
        "jq_path": jq_path,
    }


def _build_export_urls():
    configured_base_url = hass.config.external_url or hass.config.internal_url
    base_url = None

    if configured_base_url:
        base_url = str(configured_base_url).rstrip("/") + EXPORT_LOCAL_PATH

    urls = {}
    items = []

    for registry_name, files in EXPORT_FILES.items():
        json_relative_url = EXPORT_LOCAL_PATH + "/" + files["json"]
        csv_relative_url = EXPORT_LOCAL_PATH + "/" + files["csv"]

        json_url = base_url + "/" + files["json"] if base_url else None
        csv_url = base_url + "/" + files["csv"] if base_url else None

        urls[registry_name] = {
            "json": json_url or json_relative_url,
            "csv": csv_url or csv_relative_url,
            "json_absolute": json_url,
            "csv_absolute": csv_url,
            "json_relative": json_relative_url,
            "csv_relative": csv_relative_url,
        }

        items.append(
            {
                "registry": registry_name,
                "json_url": json_url,
                "json_relative_url": json_relative_url,
                "csv_url": csv_url,
                "csv_relative_url": csv_relative_url,
            }
        )

    return urls, items, base_url


# -----------------------------
# Service (response data)
# -----------------------------


@service("pyscript.refresh_ha_registry_dump", supports_response="only")
def refresh_ha_registry_dump(request_id=None):
    """yaml
    name: Refresh HA Registry Dump
    description: Run the Home Assistant registry exporter and return the generated registry export URLs.

    fields:
      request_id:
        name: Request ID
        description: Optional label for this request. If omitted, one is generated automatically and echoed in the response.
        example: inventory-refresh
        selector:
          text:

    response:
      schema_id:
        description: Stable schema identifier
      version:
        description: Schema version
      request_id:
        description: Provided or auto-generated request identifier
      meta:
        description: Summary metadata about the export run
      errors:
        description: Any validation or exporter errors
      urls:
        description: Registry-keyed object containing the preferred JSON and CSV URLs plus absolute and relative variants
      urls_json:
        description: JSON string of the registry-keyed URL object for templating
      items:
        description: Registry export records with JSON and CSV URLs
      items_json:
        description: JSON string of export records for templating
    """
    rid = _as_request_id(request_id)
    process_result = task.executor(_run_exporter)
    urls, items, base_url = _build_export_urls()
    errors = []

    if not process_result.get("ok"):
        errors.append(
            {
                "code": "EXPORT_FAILED",
                "message": process_result.get("stderr") or "Registry export failed",
                "returncode": process_result.get("returncode"),
            }
        )

    try:
        urls_json = json.dumps(urls)
        items_json = json.dumps(items)
    except Exception as error:
        errors.append(
            {
                "code": "JSON_DUMPS_FAILED",
                "message": str(error),
            }
        )
        urls_json = "{}"
        items_json = "[]"

    if process_result.get("ok"):
        log.info(
            "ha_registry_export: request_id=%r count=%d duration_seconds=%s"
            % (rid, len(items), process_result.get("duration_seconds"))
        )
    else:
        log.error(
            "ha_registry_export: request_id=%r failed=%s"
            % (rid, process_result.get("stderr") or "unknown error")
        )

    return {
        "schema_id": SCHEMA_ID,
        "version": SCHEMA_VERSION,
        "request_id": rid,
        "meta": {
            "ok": bool(process_result.get("ok")),
            "count": len(items),
            "base_url": base_url,
            "relative_base_path": EXPORT_LOCAL_PATH,
            "duration_seconds": process_result.get("duration_seconds"),
            "returncode": process_result.get("returncode"),
            "exporter_path": process_result.get("exporter_path"),
            "bash_path": process_result.get("bash_path"),
            "jq_path": process_result.get("jq_path"),
        },
        "errors": errors,
        "urls": urls,
        "urls_json": urls_json,
        "items": items,
        "items_json": items_json,
    }
