"""Two date conventions can legitimately diverge at a timezone boundary.

External civil-date anchor: China New Year 2024 is 2024-02-10 per HKO;
this test checks the *same instant* read in Rome versus UTC+8.
"""
from app.engines import BirthInput
from app.quality import QualityAuditRequest, calculation_quality_audit


def test_timezone_boundary_exposes_two_actual_lunar_dates_without_mutating_chart():
    result = calculation_quality_audit(QualityAuditRequest(birth=BirthInput(
        birth_datetime='2024-02-09T20:00', timezone='Europe/Rome')))
    snapshot = result['calculation_snapshot']
    assert snapshot['local_effective_gregorian_date'] == '2024-02-09'
    assert snapshot['lunar_date']['year'] == 2023
    assert snapshot['lunar_date']['month'] == 12
    assert snapshot['lunar_date']['day'] == 30
    assert snapshot['china_reference_gregorian_date'] == '2024-02-10'
    assert (snapshot['china_reference_lunar_date']['year'],
            snapshot['china_reference_lunar_date']['month'],
            snapshot['china_reference_lunar_date']['day']) == (2024, 1, 1)
    assert result['review_needed'] is True
    assert 'china_lunar_date_basis_disagreement' in {f['code'] for f in result['flags']}


def test_same_beijing_clock_basis_has_no_timezone_disagreement():
    result = calculation_quality_audit(QualityAuditRequest(birth=BirthInput(
        birth_datetime='2024-02-10T12:00', timezone='Asia/Shanghai')))
    snapshot = result['calculation_snapshot']
    assert snapshot['local_effective_gregorian_date'] == '2024-02-10'
    assert snapshot['china_reference_gregorian_date'] == '2024-02-10'
    assert snapshot['lunar_date'] == snapshot['china_reference_lunar_date']
    assert 'china_lunar_date_basis_disagreement' not in {f['code'] for f in result['flags']}


def test_other_timezone_without_date_change_does_not_create_extra_warning():
    result = calculation_quality_audit(QualityAuditRequest(birth=BirthInput(
        birth_datetime='2024-03-12T12:00', timezone='Europe/Rome')))
    assert 'china_lunar_date_basis_disagreement' not in {f['code'] for f in result['flags']}
    assert 'cross_timezone_calendar_convention' in {f['code'] for f in result['flags']}
