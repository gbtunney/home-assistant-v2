import shutil
import subprocess
import time

EXPORTER_PATH = "/config/ha_exporter.sh"
COMMAND_TIMEOUT_SECONDS = 120
OUTPUT_LIMIT = 8000


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


@service("pyscript.refresh_ha_registry_dump", supports_response="only")
def refresh_ha_registry_dump():
    """yaml
    name: Refresh HA registry dump
    description: Runs /config/ha_exporter.sh and returns the exporter result.
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
