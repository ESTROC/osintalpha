from pathlib import Path
def test_query_recipes_are_user_selected_and_not_auto_searched():
    s=(Path(__file__).resolve().parents[1]/'static'/'console.js').read_text()
    assert "data-use-recipe" in s and "data-load-recipes" in s
    assert "recipe-save-form" in s
    assert "No procedure initiates an external request" in s
    assert 'href="/status"' in s
