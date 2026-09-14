"""Be Unique tenant skills: five names, no RAG leftovers."""

from pathlib import Path

from chatty_agent_common.skills_loader import load_skills_by_name

_SKILLS_DIR = (
    Path(__file__).resolve().parents[1] / "app" / "subagents" / "customer" / "skills"
)
_EXPECTED = [
    "info-institucional",
    "depilacion-laser",
    "faciales",
    "promociones",
    "derivacion-equipo",
]
_BANNED = (
    "search_context",
    "metadata_be-unique",
    "confirmará la disponibilidad en agenda",
)


def test_five_skill_names_load() -> None:
    skills = load_skills_by_name(_EXPECTED, search_dirs=[_SKILLS_DIR])
    assert {skill.name for skill in skills} == set(_EXPECTED)


def test_skill_markdown_has_no_rag_leftovers() -> None:
    texts: list[str] = []
    for path in _SKILLS_DIR.rglob("*.md"):
        texts.append(path.read_text(encoding="utf-8"))
    blob = "\n".join(texts)
    for banned in _BANNED:
        assert banned not in blob, f"banned string {banned!r} still in skills"
