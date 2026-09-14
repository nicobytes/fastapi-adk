from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

from google.adk.skills import load_skill_from_dir


def shared_skills_dir() -> Path:
    """Filesystem path to package-data skills shipped with chatty-agent-common."""
    root = resources.files("chatty_agent_common").joinpath("skills")
    return Path(str(root))


def load_skills_by_name(
    skill_names: list[str],
    *,
    search_dirs: list[Path],
) -> list[Any]:
    """Load skills by explicit folder name (opt-in; no directory auto-scan).

    For each name, search ``{dir}/{name}/SKILL.md`` in ``search_dirs`` order.
    The first match wins (tenant override over common). Missing names raise
    ``FileNotFoundError`` at import/startup.
    """
    if not skill_names:
        return []

    skills: list[Any] = []
    for name in skill_names:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("skill name cannot be empty")
        if cleaned.startswith("_") or "/" in cleaned or cleaned in {".", ".."}:
            raise ValueError(f"invalid skill name: {name!r}")

        matched: Path | None = None
        for search_dir in search_dirs:
            candidate = Path(search_dir) / cleaned
            if candidate.is_dir() and (candidate / "SKILL.md").is_file():
                matched = candidate
                break

        if matched is None:
            searched = ", ".join(str(Path(d) / cleaned) for d in search_dirs)
            raise FileNotFoundError(
                f"Skill {cleaned!r} not found in search_dirs "
                f"(looked for SKILL.md under: {searched})"
            )
        skills.append(load_skill_from_dir(matched))

    return skills
