import os, sys
from pathlib import Path
from dotenv import load_dotenv

# def load_env_near_exe(require_local: bool = True):
#    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
#    env_path = base / ".env"
#    if env_path.exists():
#        load_dotenv(dotenv_path=env_path, override=True)
#    elif require_local:
#        for k in ("SERPAPI_API_KEY", "NEWSAPI_KEY"):
#            os.environ.pop(k, None)
# config_env.py
import os, sys
from pathlib import Path

def _mask(v: str) -> str:
    if not v: return ""
    return v[:4] + "…" + (v[-2:] if len(v) > 6 else "")

def load_env_near_exe(require_local: bool = True, verbose: bool = False):
    """
    Load ONLY the .env that sits next to the EXE (or this file in dev).
    If require_local=True and .env is missing, clear API keys so we don't
    accidentally fall back to User/System env on fresh machines.

    Returns a small info dict you can also print/log.
    """
    try:
        from dotenv import load_dotenv, dotenv_values
    except Exception:
        load_dotenv = dotenv_values = None

    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    env_path = base / ".env"
    exists = env_path.exists()

    # Load or clear
    if exists and load_dotenv:
        load_dotenv(dotenv_path=env_path, override=True)
        src = "file"
        file_vars = dotenv_values(env_path) if dotenv_values else {}
    else:
        src = "os"
        file_vars = {}

    if not exists and require_local:
        # prevent accidental fallback to OS env
        for k in ("SERPAPI_API_KEY", "NEWSAPI_KEY"):
            os.environ.pop(k, None)

    info = {
        "exe_base": str(base),
        ".env_path": str(env_path),
        ".env_exists": exists,
        "SERPAPI_API_KEY_present": bool(os.getenv("SERPAPI_API_KEY")),
        "NEWSAPI_KEY_present": bool(os.getenv("NEWSAPI_KEY")),
        "sources": {
            "SERPAPI_API_KEY": ("file" if "SERPAPI_API_KEY" in file_vars else "os" if os.getenv("SERPAPI_API_KEY") else "missing"),
            "NEWSAPI_KEY": ("file" if "NEWSAPI_KEY" in file_vars else "os" if os.getenv("NEWSAPI_KEY") else "missing"),
        },
    }

    if verbose:
        print("[ENV] sys.frozen =", getattr(sys, "frozen", False))
        print("[ENV] sys.executable:", sys.executable)
        print("[ENV] exe base dir :", info["exe_base"])
        print("[ENV] .env path    :", info[".env_path"], f"(exists={info['.env_exists']})")
        print("[ENV] SERPAPI_API_KEY source:", info["sources"]["SERPAPI_API_KEY"],
              " value:", _mask(os.getenv("SERPAPI_API_KEY", "")))
        print("[ENV] NEWSAPI_KEY   source:", info["sources"]["NEWSAPI_KEY"],
              " value:", _mask(os.getenv("NEWSAPI_KEY", "")))

    return info