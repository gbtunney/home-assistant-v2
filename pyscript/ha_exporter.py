"""Home Assistant registry export service.

This Pyscript module exposes a Home Assistant service that runs the existing
/config/ha_exporter.sh registry exporter without requiring an SSH session.

The shell exporter remains the source of truth for the actual export format.
This wrapper only launches it, captures a bounded amount of output, and
returns a structured result to the caller.
"""

import shutil
import subprocess
import time

EXPORTER_PATH = "/config/ha_exporter.sh"
COMMAND_TIMEOUT_SECONDS = 120
OUTPUT_LIMIT = 8000


@pyscript_compile
def _run_exporter():
    """Run the registry exporter synchronously and return a structured result.

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


@service("pyscript.refresh_ha_registry_dump", supports_response="only")
def refresh_ha_registry_dump():
    """yaml
    name: Refresh HA registry dump
    description: >
      Run the existing /config/ha_exporter.sh script and refresh the Home
      Assistant registry export files under /config/www/ha_exports. The
      exporter writes the entity, device, area, label, and floor CSV/JSON
      dumps used by external inventory tooling.

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
    """
    result = task.executor(_run_exporter)

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
