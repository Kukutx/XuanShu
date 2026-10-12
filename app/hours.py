"""The double hours of one day, each sampled in its middle under the time basis a chart uses.

Shared by the pasted-chart check (which hour reproduces another program's chart) and the
hour-Qimen day strip. 子 is split at midnight into its early and late halves, which programs
place on different days.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .engines import BRANCHES, BirthInput, calculate_bazi, normalized_dt
from .timebasis import time_basis

HOUR_SLOTS = [('早子', '子', 30)] + [(b, b, i * 120) for i, b in enumerate(BRANCHES[1:], 1)] + [('晚子', '子', 23 * 60 + 30)]


def hour_slot(reading: str) -> int:
    """Index in HOUR_SLOTS of a local reading such as 2000-08-16T04:00:00."""
    hour = int(reading[11:13])
    return 0 if hour == 0 else 12 if hour == 23 else (hour + 1) // 2


def _effective_reading(base: dict, clock: datetime) -> datetime | None:
    """The reading the chart uses for a clock time; None for a time skipped or repeated by a daylight-saving switch."""
    try:
        alternative = BirthInput(**{**base, 'birth_datetime': clock.isoformat(timespec='minutes')})
        effective, _ = time_basis(normalized_dt(alternative), alternative.time_mode, alternative.longitude)
    except ValueError:
        return None
    return effective


def _clock_for_slot(base: dict, target: datetime, shift: timedelta, slot: int) -> datetime | None:
    """A valid clock time whose effective reading falls in the double hour ``slot`` on ``target``'s day.

    The guess aims at the middle of the hour and is corrected by where it lands (solar time follows
    the clock's offset). Next to a daylight-saving switch the corrections can keep landing in the
    skipped or repeated hour; the window around the guess is then scanned, and the middle of the
    longest run of clock times that land in the hour is taken.
    """
    def inside(landed: datetime | None) -> bool:
        return landed is not None and landed.date() == target.date() and hour_slot(landed.isoformat()) == slot

    clock = target - shift
    for _ in range(4):
        clock = (clock + timedelta(seconds=30)).replace(second=0, microsecond=0)
        landed = _effective_reading(base, clock)
        if landed is None:
            break
        if inside(landed) and abs(target - landed) <= timedelta(minutes=2):
            return clock
        clock += target - landed
    start, runs, run = (target - shift - timedelta(hours=3)).replace(second=0, microsecond=0), [], []
    for step in range(0, 6 * 60 + 1, 5):
        clock = start + timedelta(minutes=step)
        if inside(_effective_reading(base, clock)):
            run.append(clock)
        elif run:
            runs.append(run)
            run = []
    runs.append(run)
    longest = max(runs, key=len)
    return longest[len(longest) // 2] if longest else None


def day_hours(birth: BirthInput, basis: dict) -> tuple[list[dict], list[str]]:
    """The same day under the same rules, once per double hour, and the labels of hours left out.

    The clock time is chosen so the time the chart actually uses (solar time when selected) falls
    in each double hour, near its middle, so every hour appears once. An hour no unambiguous clock
    time reaches (a daylight-saving switch can skip or repeat it) is left out and named. The chart's
    own hour is the chart's own moment, so that cell shows exactly what the chart shows (a solar
    term or day boundary can fall between the moment and the middle of its hour).
    """
    effective = datetime.fromisoformat(basis['effective_local_reading'])
    midnight = effective.replace(hour=0, minute=0, second=0, microsecond=0)
    shift = timedelta(minutes=basis['effective_shift_minutes'])
    current = hour_slot(basis['effective_local_reading'])
    base = birth.model_dump()
    out, missing = [], []
    for i, (label, branch, minutes) in enumerate(HOUR_SLOTS):
        if i == current:
            out.append({'index': i, 'label': label, 'branch': branch, 'current': True, 'input': birth, 'bazi': calculate_bazi(birth)})
            continue
        clock = _clock_for_slot(base, midnight + timedelta(minutes=minutes), shift, i)
        if clock is None:
            missing.append(label)
            continue
        alternative = BirthInput(**{**base, 'birth_datetime': clock.isoformat(timespec='minutes')})
        out.append({'index': i, 'label': label, 'branch': branch, 'current': False, 'input': alternative, 'bazi': calculate_bazi(alternative)})
    return out, missing


def same_hour_on_day(birth: BirthInput, basis: dict, days: int) -> tuple[BirthInput, dict]:
    """The moment for the same double hour ``days`` days away, under the same time zone and time basis.

    The day counted is the one the chart uses (its solar-time day when solar time is selected), and the
    clock time is chosen as in ``day_hours``. When a daylight-saving switch leaves that hour without an
    unambiguous clock time on the new day, the nearest hour that has one is taken and the result says so.
    """
    effective = datetime.fromisoformat(basis['effective_local_reading'])
    midnight = effective.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days)
    if not 1901 <= midnight.year <= 2099:
        raise ValueError('日期须在 1901-01-01 至 2099-12-31 之间')
    shift = timedelta(minutes=basis['effective_shift_minutes'])
    slot = hour_slot(basis['effective_local_reading'])
    base = birth.model_dump()
    for candidate in sorted(range(len(HOUR_SLOTS)), key=lambda i: (abs(i - slot), -i)):
        clock = _clock_for_slot(base, midnight + timedelta(minutes=HOUR_SLOTS[candidate][2]), shift, candidate)
        if clock is not None:
            moment = BirthInput(**{**base, 'birth_datetime': clock.isoformat(timespec='minutes')})
            return moment, {'days': days, 'date': midnight.date().isoformat(), 'moment': moment.birth_datetime,
                            'requested_hour': HOUR_SLOTS[slot][0], 'hour': HOUR_SLOTS[candidate][0],
                            'hour_kept': candidate == slot}
    raise ValueError('这一天没有可用的钟表时间')
