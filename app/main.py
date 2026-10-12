"""Local web console, REST API and stateless MCP Streamable HTTP transport."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import base64
import threading
import binascii
import re
from .json_safety import strict_json_loads
from ipaddress import ip_address
from urllib.parse import urlsplit
from pathlib import Path
from .asset_paths import resource_root
from datetime import date

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

from . import __version__
from .analysis import symbolic_reading
from .ziwei_pair import ziwei_pair_overlay
from .pillar_search import PillarSearchRequest, pillars_to_dates
from .chart_import import ChartImportRequest, chart_import_check
from .almanac import DailyAlmanacRequest, daily_almanac
from .group import GroupRequest, group_relations
from .rule_matrix import RuleMatrixRequest, rule_matrix
from .ziwei_horoscope import ZiweiHoroscopeRequest, ziwei_horoscope
from .evidence import DeepReviewRequest, deep_evidence_review
from .consultation import ConsultationRequest, execute_consultation
from .extended import LunarToGregorianRequest, BirthWindowRequest, lunar_to_gregorian, birth_window
from .astronomy import get_solar_terms, chinese_lunar_date
from .exports import solar_terms_ics
from .report import ReportRequest, structured_report
from .quality import QualityAuditRequest, calculation_quality_audit
from .engines import BirthInput, calculate_bazi, calculate_ziwei, combined_chart
from .features import CalendarRequest, PairComparisonInput, PairInput, PalaceRequest, AnnualRequest, TimeAuditRequest, RuleComparisonRequest, calendar_days, compare_charts, palace_detail, annual_transformations, time_audit, rule_comparison
from .advanced import (DayunRequest, BirthBoundaryRequest, dayun_sequence, birth_boundary_map)
from .workflows import (DayOfficerRequest, TimelineRequest, DecisionMatrixRequest,
                        day_officer_calendar, annual_timeline, decision_matrix)
from .mcp import process_rpc, SUPPORTED_PROTOCOLS, MODERN_PROTOCOL, error_response, unsupported_version
from .professional_ziwei import ProfessionalZiweiRequest, professional_ziwei_chart, professional_provider_available
from .chart_audit import QimenAuditRequest, qimen_reference_audit
from .oauth_resource import config as oauth_config, is_authorized, challenge as oauth_challenge, metadata as oauth_metadata
from .qimen import QimenRequest, qimen_chart
from .date_selection import DateScanRequest, date_candidate_scan
from .life_path import LifePathRequest, life_path_review
from .chat import ChatCancelled, ChatRequest, ChatUnavailable, chat_status, run_chat

ROOT = resource_root()
app = FastAPI(title='XuanShu API', version=__version__, description='Deterministic cultural calendar/chart calculations and MCP tools. Non-predictive.')
MAX_REQUEST_BYTES = 64 * 1024


def _public_configuration_error() -> str | None:
    try:
        oauth = oauth_config()
    except ValueError as exc:
        return str(exc)
    if os.environ.get('DEPLOYMENT_MODE') != 'public':
        return None
    if not oauth and len(os.environ.get('MCP_BEARER_TOKEN', '')) < 32:
        return 'Public mode requires OAuth configuration or a random Bearer token of at least 32 characters'
    allowed = [h.strip() for h in os.environ.get('ASTRO_ALLOWED_HOSTS', '').split(',') if h.strip()]
    if not allowed or any(h == '*' for h in allowed):
        return 'Public mode requires explicit ASTRO_ALLOWED_HOSTS'
    if oauth and urlsplit(oauth['base']).hostname not in allowed:
        return 'OAuth public hostname must appear in ASTRO_ALLOWED_HOSTS'
    return None


def _validate_host(request: Request) -> bool:
    header = request.headers.get('host', '')
    # Restrict loopback mode too: otherwise a malicious website can rebind its
    # hostname to 127.0.0.1 and read an unauthenticated local calculation API.
    # 'testserver' is the FastAPI in-process TestClient host, not a public DNS name.
    if not re.fullmatch(r'(?:[A-Za-z0-9.-]+|\[[0-9a-fA-F:]+\])(?::[0-9]{1,5})?', header):
        return False
    try:
        host = urlsplit('//' + header).hostname
    except ValueError:
        return False
    allowed = {x.strip().lower() for x in os.environ.get('ASTRO_ALLOWED_HOSTS', '').split(',') if x.strip()}
    if os.environ.get('DEPLOYMENT_MODE') != 'public':
        allowed.update({'localhost', '127.0.0.1', '::1', 'testserver'})
    return bool(host) and host.lower() in allowed


def _validate_local_peer(request: Request) -> bool:
    """Deny unauthenticated local-mode access from non-loopback sockets.

    Checking Host alone is insufficient: an external client can forge the
    ``Host: localhost`` header when Uvicorn binds to 0.0.0.0. Local mode is
    intentionally *loopback-only*, even when ASTRO_ALLOWED_HOSTS is extended;
    authenticated off-machine use requires public deployment mode.
    """
    if os.environ.get('DEPLOYMENT_MODE') == 'public':
        return True
    peer = request.client.host if request.client else ''
    if peer == 'testclient':  # Starlette's in-process TestClient sentinel.
        return True
    try:
        return ip_address(peer).is_loopback
    except ValueError:
        return False


@app.middleware('http')
async def security_headers(request: Request, call_next):
    """Fail closed for public exposure and enforce a real streamed body limit."""
    issue = _public_configuration_error()
    if issue:
        return JSONResponse({'error': issue}, status_code=503)
    if not _validate_host(request):
        return JSONResponse({'error': 'Forbidden Host'}, status_code=400)
    if not _validate_local_peer(request):
        return JSONResponse({'error': 'Local mode requires a loopback peer; enable public mode for remote access'}, status_code=403)
    if request.url.path.startswith('/api/') and not _validate_origin(request):
        return JSONResponse({'error': 'Forbidden Origin'}, status_code=403)
    if request.url.path.startswith('/api/') and not _validate_auth(request):
        return JSONResponse({'error': 'Unauthorized'}, status_code=401, headers={'WWW-Authenticate': oauth_challenge()})
    if request.method in ('POST', 'PUT', 'PATCH'):
        content_length = request.headers.get('content-length')
        if content_length:
            try:
                if int(content_length) < 0:
                    return JSONResponse({'error': 'Invalid Content-Length'}, status_code=400)
                if int(content_length) > MAX_REQUEST_BYTES:
                    return JSONResponse({'error': 'Request body too large (64 KiB limit)'}, status_code=413)
            except ValueError:
                return JSONResponse({'error': 'Invalid Content-Length'}, status_code=400)
        # Chunked transfer encoding cannot bypass Content-Length checks.
        chunks, total = [], 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > MAX_REQUEST_BYTES:
                return JSONResponse({'error': 'Request body too large (64 KiB limit)'}, status_code=413)
            chunks.append(chunk)
        request._body = b''.join(chunks)  # CachedRequest makes it available to FastAPI handlers.
        if request.url.path.startswith('/api/') or request.url.path == '/mcp':
            try:
                strict_json_loads(request._body)
            except (ValueError, UnicodeError) as exc:
                if request.url.path == '/mcp':
                    return JSONResponse(error_response(None, -32700, 'Parse error'), status_code=400)
                return JSONResponse({'detail': f'Invalid JSON request: {exc}'}, status_code=400)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    if request.url.path.startswith('/api/') or request.url.path == '/mcp':
        response.headers['Cache-Control'] = 'no-store'
    elif request.url.path == '/' or request.url.path.startswith('/static/'):
        # Revalidate with the ETag on every load: an upgrade is picked up at once, unchanged files cost a 304.
        response.headers['Cache-Control'] = 'no-cache'
    return response


class StaticGzip:
    """Compress the page and its static files only. API and MCP responses stay as they are:
    the chat stream must not be buffered, and responses that echo user input are never compressed."""

    def __init__(self, app):
        self.app = app
        self.gzip = GZipMiddleware(app, minimum_size=1024)

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '') if scope['type'] == 'http' else ''
        if path == '/' or path.startswith('/static/'):
            await self.gzip(scope, receive, send)
        else:
            await self.app(scope, receive, send)


app.add_middleware(StaticGzip)


app.mount('/static', StaticFiles(directory=ROOT/'static'), name='static')


@app.get('/')
def home():
    return FileResponse(ROOT/'static'/'index.html')


@app.get('/health')
def health():
    return {'status': 'ok', 'version': __version__, 'engine': 'swisseph', 'deployment': 'local-first'}


@app.post('/api/qimen')
def qimen(request: QimenRequest):
    try:
        return qimen_chart(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/bazi')
def bazi(request: BirthInput, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return calculate_bazi(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/consultation')
def consultation(request: ConsultationRequest):
    try:
        return execute_consultation(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.get('/api/chat/status')
def chat_status_api():
    return chat_status()


@app.post('/api/chat')
def chat(request: ChatRequest):
    try:
        return run_chat(request)
    except ChatUnavailable as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/chat/stream')
async def chat_stream(request: ChatRequest):
    """The same answer as /api/chat, streamed as newline-delimited JSON events:
    tool calls as they finish, answer text as it is written, then ``done`` with the
    full result (or ``error``). Closing the connection stops the run between steps."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    stop = threading.Event()

    def emit(event: dict | None) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, event)

    def work() -> None:
        try:
            emit({'type': 'done', 'result': run_chat(request, emit=emit, cancelled=stop.is_set)})
        except ChatCancelled:
            emit({'type': 'error', 'status': 499, 'detail': '已停止生成'})
        except ChatUnavailable as exc:
            emit({'type': 'error', 'status': 503, 'detail': str(exc)})
        except ValueError as exc:
            emit({'type': 'error', 'status': 422, 'detail': str(exc)})
        except Exception as exc:  # provider or network failure; the browser shows a short reason
            logging.getLogger(__name__).exception('chat stream failed')
            emit({'type': 'error', 'status': 502, 'detail': f'{type(exc).__name__}: {str(exc)[:300]}'})
        finally:
            emit(None)

    async def events():
        loop.run_in_executor(None, work)
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield json.dumps(event, ensure_ascii=False, default=str) + '\n'
        finally:
            stop.set()  # the worker checks this between model rounds and stream events

    return StreamingResponse(events(), media_type='application/x-ndjson', headers={'X-Accel-Buffering': 'no'})


@app.post('/api/date-scan')
def date_scan(request: DateScanRequest):
    try:
        return date_candidate_scan(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/life-path')
def life_path(request: LifePathRequest):
    try:
        return life_path_review(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/deep-review')
def deep_review(request: DeepReviewRequest):
    try:
        return deep_evidence_review(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/ziwei-professional')
def ziwei_professional(request: ProfessionalZiweiRequest):
    try:
        return professional_ziwei_chart(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/qimen-reference-audit')
def audit_qimen_reference(request: QimenAuditRequest):
    try:
        return qimen_reference_audit(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/ziwei')
def ziwei(request: BirthInput, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return calculate_ziwei(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/combined')
def combined(request: BirthInput, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return combined_chart(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/analyze')
def analysis(request: BirthInput, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return symbolic_reading(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/calendar')
def calendar(request: CalendarRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return calendar_days(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/pair')
def pair(request: PairComparisonInput, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return compare_charts(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/ziwei-pair')
def ziwei_pair(request: PairInput, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return ziwei_pair_overlay(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/palace')
def palace(request: PalaceRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return palace_detail(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc



@app.post('/api/quality-audit')
def quality_audit(request: QualityAuditRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return calculation_quality_audit(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/report')
def report(request: ReportRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return structured_report(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/annual')
def annual(request: AnnualRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return annual_transformations(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/time-audit')
def audit(request: TimeAuditRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return time_audit(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/rules-compare')
def rules_compare(request: RuleComparisonRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return rule_comparison(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/lunar-to-gregorian')
def inverse_lunar(request: LunarToGregorianRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return lunar_to_gregorian(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/pillars-to-dates')
def pillar_search(request: PillarSearchRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return pillars_to_dates(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/chart-import-check')
def import_check(request: ChartImportRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return chart_import_check(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/daily-almanac')
def almanac(request: DailyAlmanacRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return daily_almanac(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/group-relations')
def group(request: GroupRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return group_relations(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/rule-matrix')
def rules_matrix(request: RuleMatrixRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return rule_matrix(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/ziwei-horoscope')
def ziwei_periods(request: ZiweiHoroscopeRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return ziwei_horoscope(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/birth-window')
def time_window(request: BirthWindowRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return birth_window(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/dayun')
def dayun_api(request: DayunRequest, http_request: Request):
    try:
        return dayun_sequence(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/birth-boundaries')
def birth_boundaries_api(request: BirthBoundaryRequest, http_request: Request):
    try:
        return birth_boundary_map(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/day-officers')
def day_officers(request: DayOfficerRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return day_officer_calendar(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/annual-timeline')
def annual_timeline_api(request: TimelineRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return annual_timeline(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.post('/api/decision-matrix')
def decision_matrix_api(request: DecisionMatrixRequest, http_request: Request):
    if not _validate_auth(http_request):
        raise HTTPException(401, detail='Unauthorized')
    try:
        return decision_matrix(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.get('/api/lunar/{day}')
def lunar(day: date):
    try:
        return {'date': day.isoformat(), 'lunar': chinese_lunar_date(day)}
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.get('/api/solar-terms/{year}.ics')
def ics(year: int, moon: bool = False):
    try:
        content = solar_terms_ics(year, moon)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    name = f'solar-terms-moon-{year}.ics' if moon else f'solar-terms-{year}.ics'
    return Response(content, media_type='text/calendar; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename="{name}"'})

@app.get('/api/capabilities')
def capabilities():
    from .mcp import TOOL_DEFS, RESOURCES, PROMPTS
    return {
        'version': __version__,
        'features': ['bazi-four-pillars', 'bazi-hidden-stems-ten-gods-relations',
                     'solar-time-clock-mean-apparent', 'ziwei-14-major-44-selected-auxiliary', 'ziwei-optional-iztro-py-professional', 'qimen-field-level-reference-audit',
                     'natal-cycles-four-twelve-label-series', 'natal-small-limit-nominal-ages', 'natal-transformations', 'palace-flying-mappings', 'palace-trine-opposite',
                     'annual-stem-overlay', 'calendar-days', 'solar-terms-ics', 'lunar-to-gregorian', 'sampled-birth-time-window',
                     'bazi-traditional-dayun', 'hour-qimen-chabu-rotating', 'modeled-birth-boundary-map', 'jianchu-day-officers', 'annual-four-transformation-timeline', 'transparent-decision-matrix', 'pair-comparison', 'ziwei-pair-overlay', 'pillar-reverse-lookup', 'external-chart-import-check', 'daily-almanac-card', 'group-relations', 'rule-sensitivity', 'rule-sensitivity-matrix', 'moon-phase-ics', 'ziwei-month-day-hour-layers', 'chart-boundary-quality-audit', 'structured-multitool-report', 'traceable-deep-evidence-review', 'stateless-question-first-consultation', 'local-profile-backups'],
        'counts': {'mcp_tools': len(TOOL_DEFS), 'mcp_resources': len(RESOURCES),
                   'mcp_prompts': len(PROMPTS), 'agent_skills': len(list((ROOT/'skills').glob('*/SKILL.md')))},
        'privacy': 'No server-side birth-record persistence; browser localStorage opt-in.',
        'professional_ziwei_provider_available': professional_provider_available(),
        'mcp_versions': sorted(SUPPORTED_PROTOCOLS, reverse=True),
        'limitations': ['Zi Wei is a partial school-specific calculation, not a full professional chart',
                        'Qimen currently implements only an explicitly specified hour-chabu rotating school profile',
                        'Solar time depends on longitude and historical timezone accuracy',
                        'Not scientifically valid for personal life predictions',
                        'External OAuth resource server requires an issuer and deployed HTTPS; no built-in account system or host is provisioned'],
    }


@app.get('/api/solar-terms/{year}')
def terms(year: int):
    if not 1901 <= year <= 2099:
        raise HTTPException(422, detail='Supported years: 1901–2099')
    return {'year': year, 'timezone': 'Asia/Shanghai', 'terms': get_solar_terms(year)}


def _validate_origin(request: Request) -> bool:
    """Browser requests must originate from this exact local host **and port**.

    A hard-coded localhost:8000 allowlist previously broke the Web UI when
    Uvicorn used another port, while also trusting a different local port.
    Public origins remain opt-in through MCP_ALLOWED_ORIGINS only.
    """
    origin = request.headers.get('origin')
    if not origin:
        return True  # Native clients don't send Origin; authorization still applies.
    configured = {x.strip().rstrip('/') for x in os.environ.get('MCP_ALLOWED_ORIGINS', '').split(',') if x.strip()}
    if origin in configured:
        return True
    if os.environ.get('DEPLOYMENT_MODE') == 'public':
        return False
    try:
        parsed = urlsplit(origin)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
            return False
        # The Host has already passed _validate_host(). Scheme and port are
        # compared against the actual request, not another local service.
        return origin == str(request.base_url).rstrip('/')
    except ValueError:
        return False


def _validate_auth(request: Request) -> bool:
    # Local development without credentials is intentionally restricted to loopback.
    if not os.environ.get('MCP_BEARER_TOKEN') and oauth_config() is None:
        return True
    return is_authorized(request.headers.get('authorization', ''))


@app.get('/.well-known/oauth-protected-resource')
@app.get('/.well-known/oauth-protected-resource/mcp')
def oauth_protected_resource():
    try:
        return JSONResponse(oauth_metadata(), headers={'Cache-Control': 'public, max-age=300'})
    except ValueError:
        raise HTTPException(status_code=404, detail='OAuth is not enabled')


def _mcp_http_error(payload: dict, code: int, message: str, status: int = 400) -> JSONResponse:
    rpc_id = payload.get('id')
    if type(rpc_id) not in (str, int):
        rpc_id = None
    return JSONResponse(error_response(rpc_id, code, message), status_code=status)


def _decode_mcp_name(value: str) -> str:
    if value.startswith('=?base64?') and value.endswith('?='):
        try:
            return base64.b64decode(value[9:-2], validate=True).decode('utf-8')
        except (UnicodeError, ValueError, binascii.Error) as exc:
            raise ValueError('Invalid Mcp-Name encoding') from exc
    if any(ord(char) < 32 or ord(char) > 126 for char in value):
        raise ValueError('Invalid Mcp-Name header characters')
    return value


@app.post('/mcp')
async def mcp(request: Request):
    if not _validate_origin(request):
        return JSONResponse({'error': 'Forbidden Origin'}, status_code=403)
    if not _validate_auth(request):
        return JSONResponse({'error': 'Unauthorized'}, status_code=401, headers={'WWW-Authenticate': oauth_challenge()})
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Parse error'}}, status_code=400)
    if not isinstance(payload, dict):
        return JSONResponse({'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'Batch requests not supported'}}, status_code=400)
    header_version = request.headers.get('mcp-protocol-version')
    if header_version and header_version not in SUPPORTED_PROTOCOLS:
        return JSONResponse(unsupported_version(payload.get('id') if type(payload.get('id')) in (str, int) else None, header_version), status_code=400)
    params = payload.get('params')
    meta = params.get('_meta') if isinstance(params, dict) else None
    body_version = meta.get('io.modelcontextprotocol/protocolVersion') if isinstance(meta, dict) else None
    modern = header_version == MODERN_PROTOCOL or body_version == MODERN_PROTOCOL
    if modern:
        if header_version != MODERN_PROTOCOL or body_version != MODERN_PROTOCOL:
            return _mcp_http_error(payload, -32020, 'MCP protocol header and request metadata must both be 2026-07-28')
        if request.headers.get('mcp-method') != payload.get('method'):
            return _mcp_http_error(payload, -32020, 'Mcp-Method header missing or does not match request')
        if not request.headers.get('content-type', '').startswith('application/json'):
            return _mcp_http_error(payload, -32020, 'Content-Type must be application/json')
        accept = request.headers.get('accept', '')
        if 'application/json' not in accept or 'text/event-stream' not in accept:
            return _mcp_http_error(payload, -32020, 'MCP Accept must include application/json and text/event-stream')
        field = {'tools/call':'name', 'prompts/get':'name', 'resources/read':'uri'}.get(payload.get('method'))
        if field:
            raw = request.headers.get('mcp-name')
            try:
                actual = _decode_mcp_name(raw) if raw is not None else None
            except ValueError as exc:
                return _mcp_http_error(payload, -32020, str(exc))
            if actual is None or actual != (params.get(field) if isinstance(params, dict) else None):
                return _mcp_http_error(payload, -32020, 'Mcp-Name missing or mismatched')
    elif body_version is not None:
        if not isinstance(body_version, str):
            return _mcp_http_error(payload, -32602, 'protocolVersion must be a string')
        if body_version not in SUPPORTED_PROTOCOLS:
            return JSONResponse(unsupported_version(payload.get('id') if type(payload.get('id')) in (str, int) else None, body_version), status_code=400)
    response = process_rpc(payload)
    if response is None:
        return Response(status_code=202)
    if modern and response.get('error', {}).get('code') == -32601:
        return JSONResponse(response, status_code=404)
    if modern and response.get('error', {}).get('code') in (-32600, -32602):
        return JSONResponse(response, status_code=400)
    return JSONResponse(response)


@app.get('/mcp')
async def mcp_get(request: Request):
    if not _validate_origin(request):
        return JSONResponse({'error': 'Forbidden Origin'}, status_code=403)
    if not _validate_auth(request):
        return JSONResponse({'error': 'Unauthorized'}, status_code=401, headers={'WWW-Authenticate': oauth_challenge()})
    return Response(status_code=405, headers={'Allow': 'POST'})


@app.delete('/mcp')
async def mcp_delete():
    return Response(status_code=405, headers={'Allow':'POST'})
