"""
Centralized settings for DianaOS.

pydantic-settings is NOT currently declared in requirements.txt, so it is
not used here. This module uses plain `pydantic.BaseModel`
(already an approved dependency) populated by hand from os.environ, which
gives the same "fail loud on missing required values" behavior without
adding a new package. If pydantic-settings is approved later, this module
can be swapped for a `BaseSettings` subclass with no change to callers -
they only ever import `settings` from here.

Profiles:
- local        loopback bind, auth optional (default off), docs on
- lan          bind wider, auth REQUIRED, CORS must be explicitly scoped
- hosted-demo  auth REQUIRED, docs OFF unless explicitly re-enabled
- test         same shape as local, used by the test suite

Every profile can still be overridden by explicit env vars
(DIANA_REQUIRE_AUTH, DIANA_ENABLE_DOCS, CORS_ORIGINS, ...) - the profile
only changes the *defaults*, and lan/hosted-demo add fail-loud guards so a
misconfigured deploy can't silently fall back to something insecure.
"""
from __future__ import annotations

import os
from enum import Enum

from pydantic import BaseModel


class Profile(str, Enum):
    LOCAL = "local"
    LAN = "lan"
    HOSTED_DEMO = "hosted-demo"
    TEST = "test"


class Settings(BaseModel):
    profile: Profile
    host: str
    port: int
    require_auth: bool
    enable_docs: bool
    cors_origins: list[str]
    diana_username: str | None = None
    diana_password: str | None = None


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _profile_defaults(profile: Profile) -> dict:
    if profile == Profile.LOCAL:
        return dict(
            host="127.0.0.1",
            require_auth=False,
            enable_docs=True,
            cors_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        )
    if profile == Profile.LAN:
        return dict(host="0.0.0.0", require_auth=True, enable_docs=True, cors_origins=[])
    if profile == Profile.HOSTED_DEMO:
        return dict(host="0.0.0.0", require_auth=True, enable_docs=False, cors_origins=[])
    if profile == Profile.TEST:
        return dict(
            host="127.0.0.1",
            require_auth=False,
            enable_docs=True,
            cors_origins=["http://127.0.0.1:5173"],
        )
    raise ValueError(f"Unknown profile: {profile}")  # pragma: no cover - Enum guards this


def load_settings() -> Settings:
    raw_profile = os.getenv("DIANA_PROFILE", "local").strip().lower()
    try:
        profile = Profile(raw_profile)
    except ValueError as exc:
        allowed = ", ".join(p.value for p in Profile)
        raise RuntimeError(
            f"Invalid DIANA_PROFILE='{raw_profile}'. Allowed: {allowed}"
        ) from exc

    defaults = _profile_defaults(profile)

    require_auth = _env_bool("DIANA_REQUIRE_AUTH", defaults["require_auth"])
    enable_docs = _env_bool("DIANA_ENABLE_DOCS", defaults["enable_docs"])

    cors_env = os.getenv("CORS_ORIGINS", "")
    cors_origins = [o.strip() for o in cors_env.split(",") if o.strip()] or defaults["cors_origins"]

    username = os.getenv("DIANA_USERNAME", "").strip() or None
    password = os.getenv("DIANA_PASSWORD", "").strip() or None

    if profile in (Profile.LAN, Profile.HOSTED_DEMO):
        if not cors_origins:
            raise RuntimeError(
                f"Profile '{profile.value}' requires CORS_ORIGINS to be set explicitly "
                "(no wildcard, no silent localhost default)."
            )
        if not require_auth:
            raise RuntimeError(
                f"Profile '{profile.value}' requires DIANA_REQUIRE_AUTH=true "
                "(it cannot be disabled on this profile)."
            )
        if not (username and password):
            raise RuntimeError(
                f"Profile '{profile.value}' requires DIANA_USERNAME and DIANA_PASSWORD "
                "to be set - refusing to start with auth required but no credentials."
            )

    return Settings(
        profile=profile,
        host=os.getenv("DIANA_HOST", defaults["host"]),
        port=int(os.getenv("DIANA_PORT", "8000")),
        require_auth=require_auth,
        enable_docs=enable_docs,
        cors_origins=cors_origins,
        diana_username=username,
        diana_password=password,
    )


settings = load_settings()
