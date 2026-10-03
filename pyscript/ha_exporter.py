import shutil
import subprocess
import time

EXPORTER_PATH = "/config/ha_exporter.sh"
EXPORT_LOCAL_PATH = "/local/ha_exports"
COMMAND_TIMEOUT_SECONDS = 120
OUTPUT_LIMIT = 8000

EXPORT_FILES = {
    "json": {
        "entities": "ha_entities_raw.json",
        "devices": "ha_devices_raw.json",
        "areas": "ha_areas_raw.json",
        "labels": "ha_labels_raw.json",
        "floors": "ha_floors_raw.json",
    },
    "csv": {
        "entities": "ha_entities_raw.csv",
        "devices": "ha_devices_raw.csv",
        "areas": "ha_areas_raw.csv",
        "labels": "ha_labels_raw.csv",
        "floors": "ha_floors_raw.csv",
    },
}


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

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""

    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "duration_seconds": round(time.time() - started_at, 3),
        "stdout": stdout[-OUTPUT_LIMIT:],
        "stderr": stderr[-OUTPUT_LIMIT:],
        "exporter_path": EXPORTER_PATH,
        "bash_path": bash_path,
        "jq_path": jq_path,
    }


def _export_urls():
    configured_base_url = hass.config.external_url or hass.config.internal_url
    absolute_base_url = None

    if configured_base_url:
        absolute_base_url = (
            str(configured_base_url).rstrip("/") + EXPORT_LOCAL_PATH
        )

    urls = {
        "base_url": absolute_base_url,
        "relative_base_path": EXPORT_LOCAL_PATH,
        "json": {},
        "csv": {},
    }

    for format_name, files in EXPORT_FILES.items():
        for registry_name, file_name in files.items():
            relative_url = EXPORT_LOCAL_PATH + "/" + file_name
            absolute_url = (
                absolute_base_url + "/" + file_name
                if absolute_base_url
                else None
            )
            urls[format_name][registry_name] = {
                "url": absolute_url,
                "relative_url": relative_url,
            }

    return urls


# -----------------------------
# Service (response data)
# -----------------------------


@service("pyscript.refresh_ha_registry_dump", supports_response="only")
def refresh_ha_registry_dump():
    """yaml
    name: Refresh HA Registry Dump
    description: Run the Home Assistant registry exporter and return the generated entity, device, area, label, and floor export URLs.

    response:
      ok:
        description: Whether the exporter completed successfully
      returncode:
        description: Exporter process exit code, or null if it could not start
      duration_seconds:
        description: Exporter runtime in seconds
      stdout:
        description: Bounded tail of exporter standard output
      stderr:
        description: Bounded tail of exporter standard error
      exporter_path:
        description: Exporter script path
      bash_path:
        description: Bash executable used to run the exporter
      jq_path:
        description: jq executable used by the exporter
      export_urls:
        description: JSON and CSV export URLs for entities, devices, areas, labels, and floors
    """
    result = task.executor(_run_exporter)
    result["export_urls"] = _export_urls()

    if result.get("ok"):
        log.info(
            "HA registry export completed in %s seconds"
            % result.get("duration_seconds")
        )
    else:
        log.error(
            "HA registry export failed: %s"
            % (result.get("stderr") or "unknown error")
        )

    return result
