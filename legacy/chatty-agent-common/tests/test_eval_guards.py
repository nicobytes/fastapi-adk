"""Tests for deterministic user-facing output guards."""

from chatty_agent_common.eval_guards import find_forbidden_leaks


def test_find_forbidden_leaks_detects_handoff_meta_commentary() -> None:
    text = (
        "Dado que el último mensaje del usuario fue puramente informativo "
        "(ejemplo de handoff y estado interno), esperaré su próxima "
        "intervención conversacional."
    )
    leaks = find_forbidden_leaks(text)
    assert "handoff" in leaks
    assert "puramente informativo" in leaks
    assert "esperaré" in leaks


def test_find_forbidden_leaks_allows_normal_whale_reply() -> None:
    text = (
        "¡Qué plan tan chévere! El avistamiento de ballenas en Nuquí es "
        "una experiencia increíble. ¿Te cuento qué incluye el tour?"
    )
    assert find_forbidden_leaks(text) == []


def test_find_forbidden_leaks_detects_chatty_activate_token() -> None:
    assert "[chatty_activate]" in find_forbidden_leaks("[CHATTY_ACTIVATE]")
