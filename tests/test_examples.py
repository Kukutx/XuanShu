"""Keep the committed public reference fixture in sync with computation."""
import json
from pathlib import Path

from app.engines import BirthInput, combined_chart
from app.analysis import symbolic_reading


def test_reference_fixture_exact():
    p = Path(__file__).resolve().parent.parent / 'examples/reference-2000-08-16.json'
    fixture = json.loads(p.read_text(encoding='utf-8'))
    inp = BirthInput.model_validate(fixture['input'])
    assert combined_chart(inp) == fixture['result']
    assert symbolic_reading(inp) == fixture['symbolic_reading']


def test_expanded_ziwei_preserves_independent_legacy_fixture():
    """New stars must not silently alter the previously verified 32 natal stars."""
    p = Path(__file__).resolve().parent.parent / 'examples/reference-2000-08-16-baseline.json'
    fixture = json.loads(p.read_text(encoding='utf-8'))
    actual = combined_chart(BirthInput.model_validate(fixture['input']))
    old = fixture['result']
    assert actual['bazi'] == old['bazi']
    for key in ('lunar_date','ming_palace','shen_palace','five_elements_bureau','bureau_number',
                'birth_year_transformations','transformation_school','time_basis'):
        assert actual['ziwei'][key] == old['ziwei'][key], key
    for star, branch in old['ziwei']['star_positions'].items():
        assert actual['ziwei']['star_positions'][star] == branch, star
    for current, original in zip(actual['ziwei']['palaces'], old['ziwei']['palaces']):
        assert current['name'] == original['name']
        assert current['main_stars'] == original['main_stars']
        assert sorted(current['auxiliary_star_groups']['original_selected']) == sorted(original['auxiliary_stars'])
        assert current['decade'] == original['decade']
        assert current['palace_flying_transformations'] == original['palace_flying_transformations']
