# 019 — Hub SSL Fallback for Corporate/Institutional Networks

**Date:** 2026-02-25

## Background

Some PCs in research labs cannot download `.scoda` packages from GitHub
due to SSL certificate verification failures.  The Hub index (GitHub Pages)
sometimes loads, but package downloads (GitHub Releases → `objects.githubusercontent.com`)
fail with `ssl.c:1010 CERTIFICATE_VERIFY_FAILED`.

Root cause: corporate/institutional SSL inspection proxies intercept HTTPS
traffic and re-sign it with their own CA certificate.  Browsers use the
Windows certificate store (which includes the proxy CA), but Python's
`urllib` uses its own bundled CA certificates which do not.

## Changes

### `core/scoda_engine_core/hub_client.py`

**Windows certificate store integration:**
- `_load_windows_store_certs(ctx)` — loads certificates from Windows "ROOT"
  and "CA" stores via `ssl.enum_certificates()`, converts DER→PEM, and
  injects them into the SSL context.
- `_create_ssl_context()` — on Windows, automatically creates an SSL context
  with system store certificates loaded.  Also supports env var overrides:
  `SCODA_HUB_SSL_CERT` (custom CA bundle) and `SCODA_HUB_SSL_VERIFY=0`.

**SSL error separation:**
- New `HubSSLError(HubConnectionError)` exception — allows the GUI to
  distinguish SSL errors from other network failures.
- `_is_ssl_error(exc)` helper — detects SSL errors including those wrapped
  in `urllib.error.URLError`.

**`ssl_noverify` parameter:**
- `fetch_hub_index(ssl_noverify=False)` and `download_package(ssl_noverify=False)`
  accept an explicit flag to skip SSL verification.
- When `ssl_noverify=True`, uses `_create_noverify_ssl_context()` directly.
- The library does NOT auto-retry; control stays with the GUI layer.

### `scoda_engine/gui.py`

**Wait cursor:**
- Hub index fetch and package downloads show a wait cursor while HTTPS
  requests are in progress, restored on completion or error.

**SSL fallback dialog:**
- When `HubSSLError` is caught, a dialog is shown explaining the situation:
  "SSL certificate verification failed" with context about corporate proxies.
- User chooses "Yes, continue" or "No, cancel".
- "Remember this choice" checkbox — persists the decision to settings.

**Settings persistence:**
- `ScodaDesktop.cfg` (JSON) saved next to the executable (frozen) or
  project root (dev).  Visible alongside `.scoda` packages.
- `_load_settings()` / `_save_settings()` with graceful error handling.
- On startup, if `ssl_noverify` was previously saved, uses it immediately
  (no dialog, no delay).

**User experience flow:**
```
App start → Hub check (wait cursor)
  ├─ Success: show package list
  └─ SSL error:
       → restore cursor
       → dialog: "SSL certificate verification failed. Continue?"
           ☐ Remember this choice
       → Yes: retry with noverify (wait cursor)
       → No: cancel, log warning

Next launch (if "Remember" was checked):
  → noverify from the start, no delay
```

**i18n preparation:**
- All user-facing strings in English (Korean strings removed).

### `.gitignore`

- Added `ScodaDesktop.cfg` to prevent committing user-specific settings.

### `core/scoda_engine_core/__init__.py`

- `HubSSLError` added to public exports.

## Test Coverage

- 46 hub_client tests (was 25, +21 new):
  - `TestCreateSslContext` (7): env vars, Windows store, precedence
  - `TestLoadWindowsStoreCerts` (4): DER→PEM loading, error handling
  - `TestIsSslError` (5): SSL error detection across exception types
  - `TestFetchHubIndex` (6): success, network error, SSL error, noverify, env var
  - `TestDownloadPackage` (7): success, checksum, network error, SSL error, noverify
  - `TestExceptions` (2): hierarchy, HubSSLError caught as HubConnectionError
- All 276 tests passing.

## Architecture Decision

The SSL fallback is **GUI-driven, not library-driven**.  `hub_client.py`
raises `HubSSLError` and the GUI decides whether to retry.  This keeps the
library pure (no global state, no auto-retry) and gives the user explicit
control over security decisions.
