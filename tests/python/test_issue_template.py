"""The collector-send issue form states what a send holds and has the box the send window's link fills in."""

import re

# this repository's new-issue address, as the addon's links start
FORMS = "https://github.com/oLdpZ/oldpz-forever-ita/issues/new?template="


def test_collector_send_issue_form(root):
    text = (root / ".github/ISSUE_TEMPLATE/collector-send.yml").read_text(encoding="utf-8")
    for top in ("name:", "description:", "body:"):
        assert re.search(rf"^{top}", text, re.M), top
    assert re.search(r'^labels: \["collector-send"\]$', text, re.M)
    for field_id in ("id: dump", "id: note", "id: consent"):
        assert field_id in text, field_id
    assert "type: checkboxes" in text and text.count("required: true") >= 2
    for word in ("personaggio", "account", "reame", "posizione", "OldpZ_ForeverITA.lua", "OFIC1:", "L'ho inviato"):
        assert word in text, word
    assert not (root / ".github/ISSUE_TEMPLATE/collector-dump.yml").exists()


def test_the_link_and_the_form_agree(root):
    """The send window's link opens this form and fills its `dump` box; the check reads the box by its label."""
    from wfj.io import collector_send

    collector = (root / "addon/OldpZ_ForeverITA/Core/Collector.lua").read_text(encoding="utf-8")
    send = (root / "addon/OldpZ_ForeverITA/Core/CollectorSend.lua").read_text(encoding="utf-8")
    form = (root / ".github/ISSUE_TEMPLATE/collector-send.yml").read_text(encoding="utf-8")
    assert 'Collector.ISSUE_FORM = "collector-send.yml"' in collector
    assert f'Collector.ISSUE_URL = "{FORMS}" .. Collector.ISSUE_FORM' in collector
    assert re.search(r"^    id: dump$", form, re.M)
    assert '"&dump="' in send
    assert f'CollectorSend.PREFIX = "{collector_send.PREFIX}"' in send
    assert f"label: {collector_send.DUMP_LABEL}\n" in form
    assert "label: Permission\n" in form


def test_the_bug_link_and_the_bug_form_agree(root):
    """The report window's bug link fills the bug form's fields by their ids, and opens the idea form by name."""
    report = (root / "addon/OldpZ_ForeverITA/Core/BugReport.lua").read_text(encoding="utf-8")
    bug = (root / ".github/ISSUE_TEMPLATE/bug-report.yml").read_text(encoding="utf-8")
    assert '"bug-report.yml"' in report and '"idea.yml"' in report
    assert (root / ".github/ISSUE_TEMPLATE/idea.yml").is_file()
    fields = dict(re.findall(r'(build|version|errors) = "([a-z-]+)"', report))
    assert fields == {"build": "client-build", "version": "addon-version", "errors": "errors"}
    for field_id in fields.values():
        assert re.search(rf"^    id: {field_id}$", bug, re.M), field_id
    assert "/fita bug" in bug


def test_every_link_the_addon_ships_opens_a_form_of_this_repository(root):
    """The bug, idea, collector-send and translation-report links all start with this repository's new-issue address
    and name a form that exists; nothing points at the upstream project."""
    addon = root / "addon/OldpZ_ForeverITA"
    texts = {rel: (addon / rel).read_text(encoding="utf-8")
             for rel in ("Core/BugReport.lua", "Core/Collector.lua", "UI/OptionsText.lua")}
    assert f'local REPO = "{FORMS}"' in texts["Core/BugReport.lua"]
    assert f'Text.FIX_URL = "{FORMS}translation-report.yml"' in texts["UI/OptionsText.lua"]
    named = set()
    for text in texts.values():
        assert "zyaga" not in text.lower()
        named |= set(re.findall(r'"([a-z-]+\.yml)"', text))
        named |= set(re.findall(r'template=([a-z-]+\.yml)', text))
    assert named == {"bug-report.yml", "idea.yml", "collector-send.yml", "translation-report.yml"}
    for form in named:
        assert (root / ".github/ISSUE_TEMPLATE" / form).is_file(), form
