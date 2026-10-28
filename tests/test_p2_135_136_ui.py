"""P2-136 extracted view module is loaded first, explicitly escaped and preserved."""
from pathlib import Path
def test_safe_panel_is_modular_and_script_precedes_console():
    root=Path(__file__).resolve().parents[1]
    html=(root/'static/index.html').read_text()
    assert html.index('/assets/console_panels.js')<html.index('/assets/console.js')
    source=(root/'static/console.js').read_text()
    assert "window.OSINTAlphaPanels?.originPanel?." in source
    assert "window.OSINTAlphaPanels?.timingPanel?." in source
