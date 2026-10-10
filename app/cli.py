"""Local command-line interface. Output is always JSON except health diagnostics."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from . import __version__
from .qimen import QimenRequest, qimen_chart
from .professional_ziwei import ProfessionalZiweiRequest, professional_ziwei_chart
from .chart_audit import QimenAuditRequest, qimen_reference_audit
from .astronomy import chinese_lunar_date, get_solar_terms
from .engines import BirthInput, calculate_bazi, calculate_ziwei, combined_chart
from .extended import BirthWindowRequest, LunarToGregorianRequest, birth_window, lunar_to_gregorian
from .features import AnnualRequest, TimeAuditRequest, annual_transformations, time_audit
from .mcp import TOOL_DEFS
from .report import ReportRequest, structured_report
from .evidence import DeepReviewRequest, deep_evidence_review
from .consultation import ConsultationRequest, execute_consultation
from .quality import QualityAuditRequest, calculation_quality_audit
from .advanced import DayunRequest, BirthBoundaryRequest, dayun_sequence, birth_boundary_map
from .workflows import (DayOfficerRequest, TimelineRequest, DecisionMatrixRequest,
                        day_officer_calendar, annual_timeline, decision_matrix)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='xuanshu', description='Local calendar and natal chart algorithms')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('bazi','ziwei','combined','time-audit','annual','report','birth-window','quality-audit','timeline','dayun','birth-boundaries','qimen','ziwei-pro','deep-review'):
        p = sub.add_parser(name)
        p.add_argument('--date', required=True, help='Birth date/time ISO 8601')
        p.add_argument('--tz', default='Asia/Shanghai', help='IANA timezone')
        p.add_argument('--gender', choices=('male','female','unspecified'), default='unspecified')
        p.add_argument('--time-mode', choices=('clock','mean_solar','apparent_solar'), default='clock')
        p.add_argument('--longitude', type=float)
        p.add_argument('--late-zi', action='store_true')
        if name == 'deep-review':
            p.add_argument('--palace',choices=['命宫','兄弟宫','夫妻宫','子女宫','财帛宫','疾厄宫','迁移宫','仆役宫','官禄宫','田宅宫','福德宫','父母宫'],default='命宫')
            p.add_argument('--year',type=int,help='Optional annual transformation year')
        if name == 'ziwei-pro':
            p.add_argument('--target', help='Optional YYYY-MM-DD for flow horoscopes')
            p.add_argument('--target-hour', type=int, default=12)
        if name == 'dayun':
            p.add_argument('--periods', type=int, default=10, help='1–12 decade labels')
            p.add_argument('--direction', choices=('forward','reverse'), help='Explicit override if gender unspecified or alternative school')
        if name == 'birth-boundaries':
            p.add_argument('--radius', type=int, default=60, help='1–120 min either side')
        if name == 'birth-window':
            p.add_argument('--radius', type=int, default=30, help='Plus/minus minutes (5–120)')
            p.add_argument('--step', type=int, default=10, help='Sample every N minutes (5–60)')
        if name == 'annual': p.add_argument('--year', required=True, type=int)
        if name == 'timeline':
            p.add_argument('--year', required=True, type=int, help='First named lunar year')
            p.add_argument('--years', type=int, default=10, help='How many named lunar years (1–30)')
            p.add_argument('--palace', help='Optional natal palace name')
        if name == 'report':
            p.add_argument('--year', type=int, help='Optional named lunar year for overlays')
            p.add_argument('--audit-time', action='store_true', help='Include three-time-basis audit (requires longitude)')
            p.add_argument('--include-dayun', action='store_true', help='Add traditional decade cycle (gender or direction required)')
            p.add_argument('--dayun-direction', choices=('forward','reverse'))
            p.add_argument('--boundary-radius', type=int, help='Include modeled birth-time boundary map, 1–120 minutes')
    consult = sub.add_parser('consult', help='Question-first stateless consultation from a JSON input file')
    consult.add_argument('--input', required=True, help='UTF-8 JSON request file or - for stdin')
    officers = sub.add_parser('officers', help='Traditional twelve day-officer calendar')
    officers.add_argument('--date', required=True, help='Start Gregorian date YYYY-MM-DD')
    officers.add_argument('--days', type=int, default=14)
    officers.add_argument('--filter', nargs='*', default=[], help='Optional day officer labels')
    decision = sub.add_parser('decide', help='Compare choices with explicit user scores')
    decision.add_argument('--input', required=True, help='UTF-8 JSON file (or - to read stdin)')
    terms = sub.add_parser('terms');terms.add_argument('--year',type=int,required=True)
    lunar = sub.add_parser('lunar');lunar.add_argument('--date',required=True)
    inverse = sub.add_parser('gregorian')
    inverse.add_argument('--year',type=int,required=True);inverse.add_argument('--month',type=int,required=True)
    inverse.add_argument('--day',type=int,required=True);inverse.add_argument('--leap',action='store_true')
    sub.add_parser('tools');sub.add_parser('version')
    args=parser.parse_args(argv)
    try:
        if args.command == 'version': out={'version':__version__}
        elif args.command == 'tools': out={'tools':[x['name'] for x in TOOL_DEFS]}
        elif args.command == 'lunar': out={'date':args.date,'lunar':chinese_lunar_date(date.fromisoformat(args.date))}
        elif args.command == 'officers':
            out=day_officer_calendar(DayOfficerRequest(start_date=date.fromisoformat(args.date),
                days=args.days,filter_officers=args.filter))
        elif args.command == 'consult':
            if args.input == '-': payload=json.load(sys.stdin)
            else:
                from pathlib import Path
                payload=json.loads(Path(args.input).read_text(encoding='utf-8'))
            out=execute_consultation(ConsultationRequest.model_validate(payload))
        elif args.command == 'decide':
            if args.input == '-': payload=json.load(sys.stdin)
            else:
                from pathlib import Path
                payload=json.loads(Path(args.input).read_text(encoding='utf-8'))
            out=decision_matrix(DecisionMatrixRequest.model_validate(payload))
        elif args.command == 'gregorian':
            out=lunar_to_gregorian(LunarToGregorianRequest(lunar_year=args.year,lunar_month=args.month,lunar_day=args.day,is_leap_month=args.leap))
        elif args.command == 'terms':
            if not 1901<=args.year<=2099:raise ValueError('years must be 1901–2099')
            out={'year':args.year,'terms':get_solar_terms(args.year)}
        else:
            birth=BirthInput(birth_datetime=args.date,timezone=args.tz,gender=args.gender,
                             time_mode=args.time_mode,longitude=args.longitude,
                             late_zi_day_rollover=args.late_zi)
            if args.command=='deep-review':out=deep_evidence_review(DeepReviewRequest(birth=birth,focus_palace=args.palace,lunar_year=args.year))
            elif args.command=='ziwei-pro':out=professional_ziwei_chart(ProfessionalZiweiRequest(birth=birth,target_date=date.fromisoformat(args.target) if args.target else None,target_hour=args.target_hour))
            elif args.command=='qimen':out=qimen_chart(QimenRequest(moment=birth))
            elif args.command=='bazi':out=calculate_bazi(birth)
            elif args.command=='ziwei':out=calculate_ziwei(birth)
            elif args.command=='combined':out=combined_chart(birth)
            elif args.command=='time-audit':out=time_audit(TimeAuditRequest(birth=birth))
            elif args.command=='report':out=structured_report(ReportRequest(birth=birth,lunar_year=args.year,include_time_audit=args.audit_time,include_dayun=args.include_dayun,
                dayun_direction_override=args.dayun_direction,birth_boundary_minutes=args.boundary_radius))
            elif args.command=='birth-window':out=birth_window(BirthWindowRequest(birth=birth,uncertainty_minutes=args.radius,sample_every_minutes=args.step))
            elif args.command=='quality-audit':out=calculation_quality_audit(QualityAuditRequest(birth=birth))
            elif args.command=='dayun':out=dayun_sequence(DayunRequest(birth=birth, periods=args.periods, direction_override=args.direction))
            elif args.command=='birth-boundaries':out=birth_boundary_map(BirthBoundaryRequest(birth=birth, uncertainty_minutes=args.radius))
            elif args.command=='timeline':out=annual_timeline(TimelineRequest(birth=birth,
                start_lunar_year=args.year,years=args.years,focus_palace=args.palace))
            else:out=annual_transformations(AnnualRequest(birth=birth,lunar_year=args.year))
        print(json.dumps(out,ensure_ascii=False,indent=2))
        return 0
    except (ValueError,TypeError,OSError) as exc:
        print(f'Error: {exc}',file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
