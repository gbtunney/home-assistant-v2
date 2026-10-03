"""Home Assistant registry export service.

This Pyscript module exposes a Home Assistant service that runs the existing
/config/ha_exporter.sh registry exporter without requiring an SSH session.

The shell exporter remains the source of truth for the actual export format.
This wrapper only launches it, captures a bounded amount of output, and
returns a structured result plus the generated /local/ha_exports URLs.
"""

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
    """Run the registry exporter synchronously and return process details.

    This function is executed through task.executor() so the blocking
    subprocess call does not run on Home Assistant's event loop.
    """
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
    """Build absolute export URLs when HA has an external or internal URL.

    Relative /local/ha_exports paths are always returned as a fallback so
    callers can still resolve the files against their own Home Assistant URL.
    """
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


@service("pyscript.refresh_ha_registry_dump", supports_response="only")
def refresh_ha_registry_dump():
    """yaml
    name: Refresh HA registry dump
    description: >
      Run /config/ha_exporter.sh and refresh the Home Assistant registry
      exports under /config/www/ha_exports. The exporter writes entity,
      device, area, label, and floor data as both JSON and CSV. The response
      includes the corresponding /local/ha_exports URLs for downstream tools.

    response:
      ok:
        description: True when the exporter exited successfully.
      returncode:
        description: Shell process exit code, or null if the process could not start.
      duration_seconds:
        description: Time spent running the exporter.
      stdout:
        description: Bounded tail of the exporter's standard output.
      stderr:
        description: Bounded tail of the exporter's standard error or validation failure.
      exporter_path:
        description: Absolute path of the exporter that was invoked.
      bash_path:
        description: Bash executable found in the Home Assistant Core environment.
      jq_path:
        description: jq executable found in the Home Assistant Core environment.
      export_urls:
        description: >
          Generated entity, device, area, label, and floor URLs for both JSON
          and CSV. Absolute URLs are included when Home Assistant has an
          external_url or internal_url configured; relative /local paths are
          always included.
    """
    result = task.executor(_run_exporter)
    result["export_urls"] = _export_urls()

    if result.get("ok"):
        log.info(
            "HA registry export completed in %s seconds",
            result.get("duration_seconds"),
        )
    else:
        log.error(
            "HA registry export failed: %s",
            result.get("stderr") or "unknown error",
        )

    return result
