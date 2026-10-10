"""Strict RFC 9728 discovery and JWT verification for an external OAuth issuer.

This module is deliberately a *resource server*, not an identity provider:
passwords, account registration, client secrets and refresh tokens belong to
an external, independently secured authorization server (OIDC/OAuth).
"""
from __future__ import annotations

import hmac
import os
from functools import lru_cache
from urllib.parse import urlsplit

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

SCOPE = 'astro:read'


def _https_url(value: str) -> bool:
    if not value or len(value) > 2048:
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    try:
        return (parsed.scheme == 'https' and bool(parsed.hostname) and
                parsed.username is None and parsed.password is None and
                parsed.fragment == '' and parsed.query == '' and
                parsed.port in (None, 443))
    except ValueError:
        return False


def config() -> dict | None:
    """Return validated OAuth settings, or fail closed for partial configuration."""
    keys = ('ASTRO_OAUTH_ISSUER', 'ASTRO_OAUTH_JWKS_URL',
            'ASTRO_OAUTH_AUDIENCE', 'ASTRO_PUBLIC_BASE_URL')
    values = {name: os.environ.get(name, '').strip() for name in keys}
    if not any(values.values()):
        return None
    if not all(_https_url(value) for value in values.values()):
        raise ValueError('OAuth requires HTTPS issuer, JWKS, audience and public base URL')
    issuer, jwks, audience, base = [values[name].rstrip('/') for name in keys]
    if urlsplit(jwks).netloc != urlsplit(issuer).netloc:
        raise ValueError('OAuth JWKS URL must share the issuer HTTPS host')
    if urlsplit(audience).netloc != urlsplit(base).netloc or audience != base + '/mcp':
        raise ValueError('OAuth audience must equal ASTRO_PUBLIC_BASE_URL/mcp')
    if urlsplit(base).path not in ('', '/'):
        raise ValueError('ASTRO_PUBLIC_BASE_URL must be the HTTPS origin without path')
    return {'issuer': issuer, 'jwks': jwks, 'audience': audience,
            'base': base, 'resource_metadata': base + '/.well-known/oauth-protected-resource/mcp'}


@lru_cache(maxsize=8)
def jwks_client(url: str) -> PyJWKClient:
    # PyJWT caches complete JWKS for 5 minutes; key rotation uses bounded refresh.
    return PyJWKClient(url, cache_jwk_set=True, lifespan=300, timeout=5)


def token_ok(value: str) -> bool:
    """Offline JOSE checks before bounded JWKS lookup; deny on any failure."""
    cfg = config()
    if not cfg or not value or len(value) > 8192:
        return False
    try:
        header = jwt.get_unverified_header(value)
        if header.get('alg') not in ('RS256', 'ES256') or not isinstance(header.get('kid'), str):
            return False
        if not 1 <= len(header['kid']) <= 256:
            return False
        key = jwks_client(cfg['jwks']).get_signing_key_from_jwt(value).key
        claims = jwt.decode(value, key=key, algorithms=['RS256', 'ES256'],
                            issuer=cfg['issuer'], audience=cfg['audience'],
                            options={'require': ['sub', 'iss', 'aud', 'exp'], 'strict_aud': True},
                            leeway=10)
        if not isinstance(claims.get('sub'), str) or not claims['sub'].strip():
            return False
        scopes = claims.get('scope', claims.get('scp', ''))
        if isinstance(scopes, str):
            scopes = scopes.split(' ')
        if not isinstance(scopes, list) or SCOPE not in scopes:
            return False
        return True
    except (PyJWTError, ValueError, TypeError, OSError):
        return False


def is_authorized(header: str) -> bool:
    if not header.startswith('Bearer '):
        return False
    supplied = header[7:]
    # An enabled external OAuth issuer is the only authority in public mode:
    # a stale static development token must not bypass scope/audience checks.
    if config() is not None:
        return token_ok(supplied)
    static_token = os.environ.get('MCP_BEARER_TOKEN', '')
    return bool(static_token and hmac.compare_digest(supplied, static_token))


def challenge() -> str:
    cfg = config()
    if cfg:
        return f'Bearer resource_metadata="{cfg["resource_metadata"]}", scope="{SCOPE}"'
    return 'Bearer'


def metadata() -> dict:
    cfg = config()
    if not cfg:
        raise ValueError('External OAuth is not configured')
    return {
        'resource': cfg['audience'],
        'authorization_servers': [cfg['issuer']],
        'scopes_supported': [SCOPE],
        'bearer_methods_supported': ['header'],
        'resource_documentation': cfg['base'] + '/docs',
    }
