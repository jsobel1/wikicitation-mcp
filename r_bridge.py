# r_bridge.py
# Async bridge between FastMCP and mcp_interface.R.
# Each call spawns an Rscript subprocess and returns the parsed JSON result.

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

R_SCRIPT = Path(__file__).parent / "mcp_interface.R"
DEFAULT_TIMEOUT = 120


def _find_rscript() -> str:
    """Locate the Rscript executable in PATH or common Windows install paths."""
    rscript = shutil.which("Rscript")
    if rscript:
        return rscript
    import sys
    import glob
    if sys.platform == "win32":
        candidates = glob.glob(r"C:\Program Files\R\R-*\bin\Rscript.exe")
        if candidates:
            return sorted(candidates)[-1]
    raise RuntimeError(
        "Rscript not found in PATH. "
        "Ensure R is installed and accessible from this terminal.\n"
        "macOS/Linux: export PATH=$PATH:/usr/local/bin/R\n"
        "Windows:     add C:\\Program Files\\R\\R-x.x.x\\bin to PATH"
    )


async def call_r_async(
    tool: str,
    args: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    """
    Call mcp_interface.R asynchronously.

    Args:
        tool:    R tool name (matches switch case in mcp_interface.R).
        args:    Dictionary of tool arguments.
        timeout: Maximum seconds to wait before raising TimeoutError.

    Returns:
        Deserialized JSON result from R.

    Raises:
        ValueError:    If tool or args fail input validation.
        RuntimeError:  If R exits with error or returns error JSON.
        TimeoutError:  If R does not respond within the timeout.
    """
    if not isinstance(tool, str) or not tool.strip():
        raise ValueError("tool must be a non-empty string")
    if not isinstance(args, dict):
        raise ValueError("args must be a dict")

    payload = json.dumps({"tool": tool, "args": args}, ensure_ascii=False)
    logger.info("Calling R tool '%s'", tool)

    proc = await asyncio.create_subprocess_exec(
        _find_rscript(),
        str(R_SCRIPT),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=payload.encode("utf-8")),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5)
            except Exception:
                proc.kill()
            raise TimeoutError(
                f"R call '{tool}' exceeded timeout of {timeout}s. "
                "Increase DEFAULT_TIMEOUT in r_bridge.py or reduce input size."
            )
    finally:
        if proc.returncode is None:
            proc.kill()

    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

    if stderr:
        logger.debug("R stderr for '%s':\n%s", tool, stderr[:2000])

    if proc.returncode != 0:
        logger.error("Rscript exited with code %d for tool '%s'", proc.returncode, tool)
        raise RuntimeError(
            f"Rscript exited with code {proc.returncode}.\nstderr:\n{stderr[:2000]}"
        )

    if not stdout:
        logger.error("R returned empty stdout for tool '%s'", tool)
        raise RuntimeError(
            f"R returned nothing on stdout for tool '{tool}'.\nstderr:\n{stderr[:2000]}"
        )

    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"non-JSON R output for tool '{tool}': {exc}\n"
            f"Output start: {stdout[:500]}"
        ) from exc

    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(
            f"R error for tool '{tool}': {result.get('message', 'unknown')}"
        )

    logger.info("R tool '%s' completed successfully", tool)
    return result


def call_r(
    tool: str,
    args: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    """Synchronous wrapper around call_r_async for non-async callers."""
    return asyncio.run(call_r_async(tool, args, timeout))
