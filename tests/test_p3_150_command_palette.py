from pathlib import Path
def test_keyboard_palette_is_focus_safe():
    s=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    assert "const typing=['INPUT','TEXTAREA','SELECT'].includes(tag)" in s
    assert "s.user&&!typing" in s
    assert "e.key==='Escape'" in s
    assert "aria-modal=\"true\"" in s
