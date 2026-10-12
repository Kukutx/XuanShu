"""Deterministic reproducibility audit of one birth-chart calculation.

This is a boundary/assumption audit, not a verification of Zi Wei school tables.
The HKO entries are *published uncertainty zones*, not a fabricated correction
of the Swiss Ephemeris model. Never silently change a lunar date to match them.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .engines import BirthInput, calculate_bazi, calculate_ziwei, normalized_dt
from .astronomy import CHINA, chinese_lunar_date

HKO_REFERENCE = 'https://www.hko.gov.hk/en/gts/time/conversion.htm'
# HKO explicitly cautions the date can vary by one day for each cited new moon.
# The window is the resulting lunar month, where day numbers may stay offset.
HKO_UNCERTAIN_MONTHS = (
    (date(2057, 9, 28), date(2057, 10, 27), True),
    (date(2089, 9, 4), date(2089, 10, 3), False),
    (date(2097, 8, 7), date(2097, 9, 5), True),
)


class QualityAuditRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    birth: BirthInput
    boundary_window_minutes: int = Field(default=15, ge=1, le=1440)


def _cyclic_minutes_to_nearest(reading: datetime, target_minutes: list[int]) -> float:
    instant = reading.hour * 60 + reading.minute + reading.second / 60 + reading.microsecond / 60000000
    return round(min(min(abs(instant - t), 1440 - abs(instant - t)) for t in target_minutes), 3)


def _lunar_lookup_day(reading: datetime, late_zi_day_rollover: bool):
    """The Gregorian day whose lunar date the chart uses: the next one for 23:00-23:59 with the 23:00 day change."""
    return reading.date() + timedelta(days=1) if late_zi_day_rollover and reading.hour == 23 else reading.date()


def calculation_quality_audit(request: QualityAuditRequest) -> dict:
    inp = request.birth
    original = normalized_dt(inp)
    bazi, ziwei = calculate_bazi(inp), calculate_ziwei(inp)
    actual_reading = datetime.fromisoformat(bazi['time_basis']['effective_local_reading'])
    threshold = request.boundary_window_minutes
    flags: list[dict] = []

    def flag(code: str, severity: Literal['review', 'information'], detail: str, reference: str = ''):
        row = {'code': code, 'severity': severity, 'detail': detail}
        if reference:
            row['reference'] = reference
        flags.append(row)

    last_jie = datetime.fromisoformat(bazi['jie_boundaries']['previous']['instant'])
    next_jie = datetime.fromisoformat(bazi['jie_boundaries']['next']['instant'])
    previous_minutes = round((original - last_jie).total_seconds() / 60, 3)
    next_minutes = round((next_jie - original).total_seconds() / 60, 3)
    if min(previous_minutes, next_minutes) <= threshold:
        flag('jie_boundary', 'review',
             f'出生时刻距最近月令节气不超过 {threshold} 分钟；分钟取整或时区误差可能改变月柱。')

    # Chinese traditional hours begin at 23:00, 01:00, ..., 21:00.
    hour_minutes = _cyclic_minutes_to_nearest(actual_reading, list(range(60, 1440, 120)))
    if hour_minutes <= threshold:
        flag('hour_boundary', 'review',
             f'有效传统时刻距时辰交界仅 {hour_minutes:g} 分钟；真实出生时间误差可能影响时柱与紫微命身宫。')

    midnight_minutes = _cyclic_minutes_to_nearest(actual_reading, [0])
    day_change = _cyclic_minutes_to_nearest(actual_reading, [1380 if inp.late_zi_day_rollover else 0])
    if day_change <= threshold:
        flag('day_boundary', 'review',
             f'距当前八字换日界仅 {day_change:g} 分钟；需核对 23:00/00:00 换日流派及出生时间。')

    if inp.time_mode != 'clock' and actual_reading.date() != original.date():
        flag('solar_time_date_change', 'review',
             '地理太阳时与出生地钟表时间不在同一公历日；日柱/紫微农历取日会随时制变化。')

    if inp.timezone != 'Asia/Shanghai':
        flag('cross_timezone_calendar_convention', 'information',
             '出生地按选定 IANA 时区解释时刻；农历月相按现代中国 UTC+8 天文日定义，排盘取出生地有效公历日。跨时区日界可能产生流派差异。')

    lunar_date = ziwei['lunar_date']
    # Current Zi Wei rules use the birth location's effective Gregorian date
    # to look up a modern China UTC+8 lunar calendar. At a cross-zone day
    # boundary, a user may instead expect the lunar date of the same *instant*
    # expressed in China standard time. Show both without silently changing
    # the selected school convention or pretending one is universal.
    lookup_day = _lunar_lookup_day(actual_reading, inp.late_zi_day_rollover)
    china_reference_day = _lunar_lookup_day(original.astimezone(CHINA), inp.late_zi_day_rollover)
    china_reference_lunar = (chinese_lunar_date(china_reference_day)
                             if 1901 <= china_reference_day.year <= 2099 else None)
    if china_reference_lunar is None:
        flag('china_calendar_reference_out_of_range', 'information',
             '同一瞬间的北京时间日期在本工具支持的农历范围之外，无法提供 UTC+8 对照。')
    elif china_reference_day != lookup_day:
        if (lunar_date['year'], lunar_date['month'], lunar_date['day'], lunar_date['is_leap_month']) != (
                china_reference_lunar['year'], china_reference_lunar['month'],
                china_reference_lunar['day'], china_reference_lunar['is_leap_month']):
            flag('china_lunar_date_basis_disagreement', 'review',
                 f'按出生地有效公历日 {lookup_day} 排出的农历为 '
                 f"{lunar_date['year']}年{lunar_date['month']}月{lunar_date['day']}日；"
                 f'同一绝对瞬间按北京时间 {china_reference_day} 查农历则为 '
                 f"{china_reference_lunar['year']}年{china_reference_lunar['month']}月{china_reference_lunar['day']}日。"
                 ' 两种排盘口径不同，需先确认出生地日界与选定传统流派；本工具不自动替换原命盘。')
    if lunar_date['day'] in (1, lunar_date['month_days']):
        flag('lunar_month_change', 'information',
             '出生日期位于农历月首/末日；新月日界与闰月划分需要审慎核对。')

    for start, end, differs_from_hko in HKO_UNCERTAIN_MONTHS:
        if start <= lookup_day <= end:
            status = '当前天文模型与香港天文台表中月首相差一天' if differs_from_hko else '当前月首和天文台表一致，但天文台仍提示一日不确定性'
            flag('published_new_moon_uncertainty', 'review',
                 f'香港天文台将 {start.isoformat()} 新月日期列为远期不确定边界；{status}。'
                 ' 本工具不会自动修正农历日期；月内日数也可能相差一天。', HKO_REFERENCE)
            break

    if original.year < 1949:
        flag('historical_timezone_review', 'information',
             '较早年份的出生地历史法律时制可能与后来的标准时间不同，请核对当时使用的真实钟表记录。')

    details = {
        'original_local': original.isoformat(timespec='seconds'),
        'effective_traditional_time': actual_reading.isoformat(timespec='seconds'),
        'time_mode': inp.time_mode,
        'longitude_east_degrees': inp.longitude,
        'previous_jie': bazi['jie_boundaries']['previous'],
        'next_jie': bazi['jie_boundaries']['next'],
        'minutes_since_previous_jie': previous_minutes,
        'minutes_until_next_jie': next_minutes,
        'minutes_to_nearest_hour_boundary': hour_minutes,
        'minutes_to_day_boundary': day_change,
        'minutes_to_midnight': midnight_minutes,
        'lunar_date': lunar_date,
        'local_effective_gregorian_date': actual_reading.date().isoformat(),
        'lunar_lookup_gregorian_date': lookup_day.isoformat(),
        'china_reference_gregorian_date': china_reference_day.isoformat(),
        'china_reference_lunar_date': china_reference_lunar,
        'lunar_date_basis': 'natal effective local Gregorian date, the next day for 23:00-23:59 with the 23:00 day change (not UTC+8 instant date)',
        'bazi_pillars': {name: row['text'] for name, row in bazi['pillars'].items()},
        'ziwei_ming': ziwei['ming_palace'],
        'ziwei_shen': ziwei['shen_palace'],
    }
    return {
        'system': 'chart-input-and-boundary-quality-audit',
        'review_needed': any(item['severity'] == 'review' for item in flags),
        'flags': flags,
        'calculation_snapshot': details,
        'methods': ['Swiss Ephemeris (Moshier) astronomical instants',
                    'Modern China UTC+8 lunar calendar conventions',
                    'Specified school subset for partial Zi Wei'],
        'limitations': [
            '没有边界警告不等于通过外部权威历表或紫微各流派专业认证。',
            '如遇香港天文台公开的远期新月不确定日期，只提示差异，不擅自修改计算结果。',
            '传统术数的象征解释不属于已获得科学验证的个人命运预测。',
        ],
    }
