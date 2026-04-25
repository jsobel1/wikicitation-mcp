# r_bridge.py
# Bridge asynchrone entre FastMCP et le script R mcp_interface.R.
# Chaque appel lance un sous-processus Rscript et retourne le JSON parsé.

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

# Chemin absolu vers le script R (dans le même dossier que ce fichier)
R_SCRIPT = Path(__file__).parent / "mcp_interface.R"

# Timeout global en secondes.
# Les requêtes réseau R (EuropePMC, CrossRef) peuvent être lentes.
DEFAULT_TIMEOUT = 120


def _find_rscript() -> str:
    """Localise l'exécutable Rscript dans le PATH ou aux emplacements Windows courants."""
    rscript = shutil.which("Rscript")
    if rscript:
        return rscript
    # Fallback: scan Program Files for any R installation on Windows
    import sys, glob
    if sys.platform == "win32":
        candidates = glob.glob(r"C:\Program Files\R\R-*\bin\Rscript.exe")
        if candidates:
            return sorted(candidates)[-1]  # pick latest version
    raise RuntimeError(
        "Rscript introuvable dans le PATH. "
        "Vérifiez que R est installé et accessible depuis ce terminal.\n"
        "Sur macOS/Linux : export PATH=$PATH:/usr/local/bin/R\n"
        "Sur Windows      : ajoutez C:\\Program Files\\R\\R-x.x.x\\bin à PATH"
    )


async def call_r_async(
    tool: str,
    args: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    """
    Appelle mcp_interface.R de façon asynchrone.

    Args:
        tool:    Nom de l'outil R (correspond au switch dans mcp_interface.R).
        args:    Dictionnaire des arguments de l'outil.
        timeout: Délai maximum en secondes avant levée d'une TimeoutError.

    Returns:
        Résultat désérialisé depuis le JSON retourné par R.

    Raises:
        RuntimeError: si R quitte avec un code d'erreur ou retourne un JSON
                      avec {"error": true}.
        TimeoutError: si R ne répond pas dans le délai imparti.
    """
    payload = json.dumps({"tool": tool, "args": args}, ensure_ascii=False)

    proc = await asyncio.create_subprocess_exec(
        _find_rscript(),
        str(R_SCRIPT),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(input=payload.encode("utf-8")),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise TimeoutError(
            f"L'appel R '{tool}' a dépassé le délai de {timeout}s. "
            "Essayez d'augmenter DEFAULT_TIMEOUT dans r_bridge.py, "
            "ou réduisez la taille des entrées."
        )

    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0:
        raise RuntimeError(
            f"Rscript a quitté avec le code {proc.returncode}.\n"
            f"stderr :\n{stderr[:2000]}"
        )

    if not stdout:
        raise RuntimeError(
            f"R n'a rien retourné sur stdout pour l'outil '{tool}'.\n"
            f"stderr :\n{stderr[:2000]}"
        )

    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Sortie R non-JSON pour l'outil '{tool}': {exc}\n"
            f"Début de la sortie : {stdout[:500]}"
        ) from exc

    # Propager les erreurs R explicites ({"error": true, "message": "..."})
    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(
            f"Erreur R pour l'outil '{tool}': {result.get('message', 'inconnu')}"
        )

    return result


def call_r(
    tool: str,
    args: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    """
    Version synchrone de call_r_async — utilisée dans les handlers FastMCP
    qui ne sont pas eux-mêmes async.
    """
    return asyncio.get_event_loop().run_until_complete(
        call_r_async(tool, args, timeout)
    )
