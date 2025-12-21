from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Protocol


class _Logger(Protocol):
    def info(self, msg: str) -> None: ...

    def warning(self, msg: str) -> None: ...

    def error(self, msg: str) -> None: ...


@dataclass(frozen=True)
class ChromaInitResult:
    client: object
    persisted: bool
    persist_dir: Path


def get_default_chroma_persist_dir(
    *,
    env_var: str = "SYSTEM_CHROMA_PERSIST_DIR",
    default: str = "~/.system_cli/chroma",
) -> Path:
    """Default persistence dir for ChromaDB.

    Use `SYSTEM_CHROMA_PERSIST_DIR` to override.
    """

    env = os.environ.get(env_var)
    value = Path(env) if env else Path(default)
    return value.expanduser().resolve()


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _backup_dir_name(dir_name: str) -> str:
    return f"{dir_name}_corrupt_{_timestamp()}"


def _safe_prepare_dir(persist_dir: Path) -> Path:
    persist_dir = Path(persist_dir).expanduser().resolve()
    persist_dir.mkdir(parents=True, exist_ok=True)
    return persist_dir


def create_persistent_client(
    *,
    persist_dir: Path,
    logger: _Logger,
    retry_repair: bool = True,
) -> Optional[ChromaInitResult]:
    """Create ChromaDB PersistentClient with one repair+retry attempt.

    Why: some Chroma builds can raise a pyo3 PanicException from Rust sqlite.
    Strategy: on failure, move the persistence directory aside and retry once.
    """

    persist_dir = _safe_prepare_dir(persist_dir)

    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(persist_dir))
        return ChromaInitResult(client=client, persisted=True, persist_dir=persist_dir)
    except BaseException as exc:  # includes pyo3_runtime.PanicException
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        logger.warning(
            f"⚠️ ChromaDB PersistentClient failed ({type(exc).__name__}); "
            f"persist_dir={persist_dir}"
        )

        if not retry_repair:
            return None

        try:
            backup_dir = persist_dir.parent / _backup_dir_name(persist_dir.name)
            if backup_dir.exists():
                backup_dir = persist_dir.parent / f"{backup_dir.name}_{_timestamp()}"

            # Move aside entire directory (including possibly-corrupt sqlite files)
            persist_dir.rename(backup_dir)
            logger.warning(f"🧹 Moved ChromaDB dir to backup: {backup_dir}")

            persist_dir = _safe_prepare_dir(persist_dir)

            import chromadb

            client = chromadb.PersistentClient(path=str(persist_dir))
            logger.info("✅ ChromaDB PersistentClient recovered after repair")
            return ChromaInitResult(client=client, persisted=True, persist_dir=persist_dir)
        except BaseException as repair_exc:
            if isinstance(repair_exc, (KeyboardInterrupt, SystemExit)):
                raise
            logger.error(
                f"❌ ChromaDB PersistentClient repair retry failed ({type(repair_exc).__name__}); "
                f"persist_dir={persist_dir}"
            )
            return None
