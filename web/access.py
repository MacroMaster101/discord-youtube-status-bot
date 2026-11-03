"""Cloudflare Access sign-in for the dashboard.

The Cf-Access-Authenticated-User-Email header proves nothing on its own: any
client can send it, and Cloudflare only sets it on requests that actually came
through the Access application. A request that reaches the origin directly --
over the SSH tunnel, or on a path outside the Access app -- carries whatever the
caller typed. The signed Cf-Access-Jwt-Assertion is the only trustworthy
identity, so without the team domain and AUD tag needed to verify it, Access
sign-in stays switched off rather than falling back to the header.
"""
import os
import threading

from flask import request

_verifier = None
_verifier_built = False
_lock = threading.Lock()


def _build_verifier():
    """Build the JWT verifier, or None when Access isn't configured."""
    team = os.getenv("CF_ACCESS_TEAM_DOMAIN", "").strip().removeprefix("https://").rstrip("/")
    aud = os.getenv("CF_ACCESS_AUD", "").strip()
    if not team or not aud:
        return None

    try:
        import jwt
    except ImportError:  # pragma: no cover - depends on the install
        print("CF_ACCESS_* is set but PyJWT is missing; Cloudflare Access sign-in is disabled.")
        return None

    issuer = f"https://{team}"
    # PyJWKClient caches the key set and refetches when it meets an unknown kid,
    # which is what covers Cloudflare's periodic key rotation.
    jwks = jwt.PyJWKClient(f"{issuer}/cdn-cgi/access/certs", lifespan=3600)

    def verify(token: str):
        try:
            key = jwks.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token, key, algorithms=["RS256"], audience=aud, issuer=issuer,
                options={"require": ["exp", "iat", "aud", "iss"]},
            )
        except Exception as e:
            print(f"Access JWT rejected: {e}")
            return None
        email = claims.get("email")
        return email if isinstance(email, str) and email else None

    return verify


def _get_verifier():
    """Built once, lazily, so importing this module never does network setup."""
    global _verifier, _verifier_built
    if _verifier_built:
        return _verifier
    with _lock:
        if not _verifier_built:
            _verifier = _build_verifier()
            _verifier_built = True
    return _verifier


def is_configured() -> bool:
    return _get_verifier() is not None


def identity():
    """The verified Cloudflare Access email for this request, or None."""
    verify = _get_verifier()
    if not verify:
        return None
    assertion = request.headers.get("Cf-Access-Jwt-Assertion", "").strip()
    return verify(assertion) if assertion else None


def reset_for_tests():
    """Drop the cached verifier so tests can change the environment."""
    global _verifier, _verifier_built
    with _lock:
        _verifier = None
        _verifier_built = False
