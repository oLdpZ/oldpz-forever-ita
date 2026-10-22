"""The public front door says what a player and a contributor need, in both languages where players read it."""

import re

import pytest


def _read(root, path):
    return (root / path).read_text(encoding="utf-8")


def test_readme_covers_install_use_reporting_credits_in_italian(root):
    text = _read(root, "README.md")
    for heading in ("## Cosa traduce", "## Installazione", "### Con l'app CurseForge", "### A mano",
                    "### Attivarlo nel gioco", "## Come si usa", "## Perché alcuni testi restano in inglese",
                    "## La raccolta dei testi inglesi", "## Segnalare un problema", "## Riconoscimenti",
                    "## Licenza", "## Per chi sviluppa"):
        assert heading in text, heading
    assert "OldpZ_ForeverITA" in text and "_forever_" in text
    assert "CONTRIBUTING.md" in text and "ATTRIBUTION.md" in text


def test_nothing_public_claims_to_replace_the_classic_addons(root):
    for path in ("README.md", "docs/curseforge.md", "ATTRIBUTION.md", "docs/overview.md"):
        text = _read(root, path)
        assert not re.search(r"\breplaces\b|supersede|successor|\bsucceed(s|ed)?\b|後継", text, re.IGNORECASE), path


def test_curseforge_description_is_italian_and_claims_nothing_the_addon_lacks(root):
    text = _read(root, "docs/curseforge.md")
    assert "## Description" in text and "**Project name:** oLd_pZ Forever - Traduzione Italiana" in text
    assert "### <span style=\"color:#E8C77E;\">Cosa traduce</span>" in text
    assert not re.search(r"[぀-ヿ一-鿿]", text)
    for absent in ("voice", "voce", "dizionario", "dictionary", "Japanese Voice", "foreverjapanese"):
        assert absent.lower() not in text.lower(), absent
    assert not (root / "docs/curseforge-voice.md").exists()


def test_contributing_states_the_terms_and_the_setup(root):
    text = _read(root, "CONTRIBUTING.md")
    for needle in ("inbound = outbound", "no contributor license agreement", "issue first", ".venv",
                   "make test", "make lint", "make coverage", "Never edit by hand", "provenance"):
        assert needle.lower() in text.lower(), needle


def test_licensing_names_every_source_and_the_bsd_notice(root):
    text = _read(root, "docs/legal/licensing.md")
    for needle in ("Forever client tables", "Forever quest cache", "Classic Era quest cache", "VMaNGOS",
                   "wago.tools", "pfQuest", "forever-vo", "139,877", "BSD", "IPA", "not legal advice"):
        assert needle in text, needle
    assert "GPLv2 chain" not in text
    attribution = _read(root, "ATTRIBUTION.md")
    # the fork credits the upstream code; no Japanese translation ships, so its translators and its BSD notice
    # stay upstream, as test_attribution holds
    for needle in ("WoW Forever Japanese", "Zyaga", "GPL-2.0-or-later", "Permission is hereby granted"):
        assert needle in attribution, needle
    assert not re.search(r"\bendorse(d|s)? (this|the) project\b|\bofficial\b", attribution.split("## Lineage")[0])


@pytest.mark.parametrize("form", ["translation-report.yml", "bug-report.yml", "collector-send.yml", "idea.yml"])
def test_issue_forms_speak_italian(root, form):
    """The name, every description and every consent line of a form are in Italian; nothing in it is Japanese.
    Only the labels the checks read (Report, Credit me as, Collected English, Permission) stay English."""
    text = _read(root, f".github/ISSUE_TEMPLATE/{form}")
    assert not re.search(r"[぀-ヿ一-鿿]", text), form
    assert "zyaga" not in text.lower() and "japanese" not in text.lower(), form
    lines = [ln.strip() for ln in text.splitlines()]
    checked = [ln for ln in lines if ln.startswith(("name:", "description:", "- label:"))]
    assert len(checked) >= 3, form
    italian = re.compile(r"\b(il|la|le|lo|gli|un|una|di|da|del|della|che|per|con|non|è|nel|questa|cosa)\b"
                         r"|\b[lu]n?'", re.I)
    for ln in checked:
        assert italian.search(ln), f"{form}: no Italian in: {ln[:60]}"


@pytest.mark.parametrize("form", ["translation-report.yml", "bug-report.yml", "collector-send.yml", "idea.yml"])
def test_issue_form_values_are_plain_yaml(root, form):
    """An unquoted value holds no `: ` and no ` #`: either one ends the value early or breaks the file, and
    GitHub then hides the form."""
    for n, line in enumerate(_read(root, f".github/ISSUE_TEMPLATE/{form}").splitlines(), 1):
        m = re.match(r"^\s*(?:- )?(name|description|label|title|placeholder): (.*)$", line)
        if m and not m.group(2).startswith(('"', "'", "|", ">")):
            assert ": " not in m.group(2) and " #" not in m.group(2), f"{form}:{n}: quote this value"


def test_the_report_form_keeps_the_labels_the_report_check_reads(root):
    """`wfj report` finds the sections of an issue by these labels; a translated label would hide them."""
    text = _read(root, ".github/ISSUE_TEMPLATE/translation-report.yml")
    for label in ("label: Report\n", "label: Credit me as\n", "label: Permission\n"):
        assert label in text, label


def test_issues_come_through_the_forms(root):
    assert "blank_issues_enabled: false" in _read(root, ".github/ISSUE_TEMPLATE/config.yml")
    assert _read(root, ".github/CODEOWNERS").strip()
    assert "pubblica" in _read(root, ".github/ISSUE_TEMPLATE/translation-report.yml")


def test_security_and_conduct_pages_say_how_to_report_in_both_languages(root):
    security, conduct = _read(root, "SECURITY.md"), _read(root, "CODE_OF_CONDUCT.md")
    for text in (security, conduct):
        assert "## Italiano" in text and not re.search(r"[぀-ヿ一-鿿]", text)
        assert "zyaga" not in text.lower()
    assert "Report a vulnerability" in security and "do not open a public issue" in security.lower()
    assert "Report content" in conduct and "SECURITY.md" in conduct
    assert "SECURITY.md" in _read(root, "CONTRIBUTING.md") and "CODE_OF_CONDUCT.md" in _read(root, "CONTRIBUTING.md")
    assert "security/advisories/new" in _read(root, ".github/ISSUE_TEMPLATE/config.yml")


def test_the_trademark_notice_is_on_the_public_pages(root):
    for path in ("README.md", "docs/curseforge.md"):
        text = _read(root, path)
        assert "Non è affiliato né approvato da Blizzard Entertainment" in text, path
        assert "marchi o marchi registrati di Blizzard Entertainment" in text, path
    assert "not affiliated with or endorsed by Blizzard Entertainment" in _read(root, "docs/legal/licensing.md")


def test_the_settings_command_is_the_one_the_addon_has(root):
    """Bare `/fita` prints the status; the settings open with `/fita config`."""
    slash = _read(root, "addon/OldpZ_ForeverITA/UI/Slash.lua")
    assert 'lower == "config"' in slash
    for path in ("README.md", "docs/curseforge.md", "CHANGELOG.md"):
        for line in _read(root, path).splitlines():
            if re.search(r"Options > AddOns|オプション > AddOns", line) and "/fita" in line:
                assert "/fita config" in line, f"{path}: {line[:80]}"


def test_pull_request_template_is_short_and_public(root):
    text = _read(root, ".github/pull_request_template.md")
    assert len(text.splitlines()) < 40
    for needle in ("## What changes", "## Testing", "## Changelog"):
        assert needle in text, needle
