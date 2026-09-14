"""Opt-in skill loading: first match wins; missing names fail fast."""

from __future__ import annotations

from pathlib import Path

import pytest

from chatty_agent_common.skills_loader import load_skills_by_name, shared_skills_dir


def _write_skill(root: Path, name: str, description: str = "test skill") -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
        encoding="utf-8",
    )
    return skill_dir


def test_shared_skills_dir_exists() -> None:
    assert shared_skills_dir().is_dir()


def test_load_skills_by_name_from_search_dir(tmp_path: Path) -> None:
    _write_skill(tmp_path, "demo-skill")
    skills = load_skills_by_name(
        ["demo-skill"],
        search_dirs=[tmp_path],
    )
    assert len(skills) == 1
    assert skills[0].name == "demo-skill"


def test_tenant_override_wins(tmp_path: Path) -> None:
    common = tmp_path / "common"
    tenant = tmp_path / "tenant"
    common.mkdir()
    tenant.mkdir()
    _write_skill(common, "demo-skill", description="common")
    _write_skill(tenant, "demo-skill", description="override")

    skills = load_skills_by_name(
        ["demo-skill"],
        search_dirs=[tenant, common],
    )
    assert len(skills) == 1
    assert skills[0].description == "override"


def test_missing_skill_fails_fast(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does-not-exist"):
        load_skills_by_name(
            ["does-not-exist"],
            search_dirs=[tmp_path, shared_skills_dir()],
        )


def test_empty_name_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        load_skills_by_name([""], search_dirs=[shared_skills_dir()])
