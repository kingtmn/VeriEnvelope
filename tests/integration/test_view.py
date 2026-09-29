import json
from pathlib import Path

from tests.paths import METHOD
from verienvelope.run import run_case
from verienvelope.view import _text, render_html, write_html

QUESTIONS = [
    "这个组件是谁？",
    "哪个版本？",
    "实测能做什么？",
    "为什么相信？",
    "哪些地方没有验证？",
    "已知失败在哪里？",
    "原始证据在哪里？",
    "有没有历史修正？",
]


def test_text_is_escaped() -> None:
    assert "<script>" not in _text("<script>alert(1)</script>")
    assert _text(None) == "UNKNOWN"
    assert _text("") == "UNKNOWN"


def test_viewer_answers_the_eight_questions(tmp_path: Path) -> None:
    result = run_case(METHOD, METHOD / "cases" / "echo_match.json", tmp_path / "evidence")
    html = render_html(result)
    for question in QUESTIONS:
        assert question in html
    assert "本页没有总分" in html
    assert "测量管线自审记录，不是组件验证结论" in html
    assert "不能推出未测范围内没有失败" in html
    assert result["evidence_dir"] in html
    assert result["capabilities"][0]["testable_statement"] in html
    assert "UNKNOWN" in html  # commit is absent
    assert ">demonstrated<" in html or "demonstrated" in html
    section = html.split("<section>", 1)[1]
    assert "结果" in section
    assert "声明范围" in section
    assert section.index("结果") < section.index("声明范围")
    destination = tmp_path / "preview" / "index.html"
    result_path = tmp_path / "evidence" / result["evidence_dir"] / "result.json"
    write_html(result_path, destination)
    written = destination.read_text(encoding="utf-8")
    assert written == html
    original = json.loads(result_path.read_text(encoding="utf-8"))
    assert original["admission"] == "insufficient"
    emptied = json.loads(json.dumps(result))
    emptied["envelope"]["known_limits"] = []
    emptied["capabilities"][0]["envelope"]["known_limits"] = []
    emptied["admission"] = "admitted"
    emptied["admission_reasons"] = []
    shown = render_html(emptied)
    assert "None empirically established" in shown
    assert "No limits" not in shown
    assert "fitness for your use" in shown
    assert "不是 certified" in shown
    assert "Certified" not in shown
