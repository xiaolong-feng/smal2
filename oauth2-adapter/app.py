import base64
import html
import json
import os
import secrets
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PORT = int(os.getenv("PORT", "8080"))
PUBLIC_BASE = os.getenv("ADAPTER_PUBLIC_BASE", "http://202.122.38.207:19090").rstrip("/")

SATOSA_DISCOVERY_URL = os.getenv(
    "SATOSA_DISCOVERY_URL", "https://satosa/.well-known/openid-configuration"
)
SATOSA_AUTHORIZATION_ENDPOINT = os.getenv("SATOSA_AUTHORIZATION_ENDPOINT")
SATOSA_TOKEN_ENDPOINT = os.getenv("SATOSA_TOKEN_ENDPOINT")
SATOSA_USERINFO_ENDPOINT = os.getenv("SATOSA_USERINFO_ENDPOINT")
SATOSA_CLIENT_ID = os.getenv("SATOSA_CLIENT_ID", "oauth2-adapter")
SATOSA_CLIENT_SECRET = os.getenv("SATOSA_CLIENT_SECRET", "adapter-secret")
SATOSA_REDIRECT_URI = os.getenv("SATOSA_REDIRECT_URI", f"{PUBLIC_BASE}/callback")
SATOSA_SCOPE = os.getenv("SATOSA_SCOPE", "openid profile email")
VERIFY_TLS = os.getenv("SATOSA_VERIFY_TLS", "false").lower() in {"1", "true", "yes", "on"}

OAUTH2_CLIENT_ID = os.getenv("OAUTH2_CLIENT_ID", "oauth2-test-app")
OAUTH2_CLIENT_SECRET = os.getenv("OAUTH2_CLIENT_SECRET", "oauth-test-secret")
OAUTH2_CLIENT_REDIRECT_URI = os.getenv(
    "OAUTH2_CLIENT_REDIRECT_URI", "http://202.122.38.207:19091/callback"
)

CODE_TTL = int(os.getenv("OAUTH2_CODE_TTL", "600"))
ACCESS_TOKEN_TTL = int(os.getenv("OAUTH2_ACCESS_TOKEN_TTL", "3600"))

CLIENTS = {
    OAUTH2_CLIENT_ID: {
        "client_secret": OAUTH2_CLIENT_SECRET,
        "redirect_uris": [OAUTH2_CLIENT_REDIRECT_URI],
    }
}

PENDING_AUTH = {}
AUTHORIZATION_CODES = {}
ACCESS_TOKENS = {}
STORE_LOCK = threading.Lock()


def now():
    return int(time.time())


def json_request(url, method="GET", data=None, headers=None, bearer_token=None):
    headers = dict(headers or {})
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    context = ssl.create_default_context() if VERIFY_TLS else ssl._create_unverified_context()
    with urllib.request.urlopen(request, context=context, timeout=20) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw)


def discovery():
    metadata = json_request(SATOSA_DISCOVERY_URL)
    return {
        "authorization_endpoint": SATOSA_AUTHORIZATION_ENDPOINT
        or metadata["authorization_endpoint"],
        "token_endpoint": SATOSA_TOKEN_ENDPOINT or metadata["token_endpoint"],
        "userinfo_endpoint": SATOSA_USERINFO_ENDPOINT or metadata.get("userinfo_endpoint"),
        "raw": metadata,
    }


def render_json(value):
    return html.escape(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def first(query, name, default=""):
    values = query.get(name)
    if not values:
        return default
    return values[0]


def parse_basic_auth(header):
    if not header or not header.startswith("Basic "):
        return None, None
    try:
        decoded = base64.b64decode(header[6:]).decode("utf-8")
    except Exception:
        return None, None
    client_id, sep, client_secret = decoded.partition(":")
    if not sep:
        return None, None
    return client_id, client_secret


def add_query(url, params):
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urllib.parse.urlencode(params)}"


def redirect_error(redirect_uri, error, state=None, description=None):
    params = {"error": error}
    if description:
        params["error_description"] = description
    if state:
        params["state"] = state
    return add_query(redirect_uri, params)


def cleanup_expired():
    cutoff = now()
    with STORE_LOCK:
        for key, item in list(PENDING_AUTH.items()):
            if item["created_at"] + CODE_TTL < cutoff:
                del PENDING_AUTH[key]
        for key, item in list(AUTHORIZATION_CODES.items()):
            if item["created_at"] + CODE_TTL < cutoff:
                del AUTHORIZATION_CODES[key]
        for key, item in list(ACCESS_TOKENS.items()):
            if item["created_at"] + ACCESS_TOKEN_TTL < cutoff:
                del ACCESS_TOKENS[key]


def render_page(title, body, status=HTTPStatus.OK):
    return status, f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ margin: 0; padding: 32px; font-family: Arial, sans-serif; background: #f7f8fa; color: #202124; }}
    main {{ max-width: 1040px; margin: 0 auto; }}
    h1 {{ margin: 0 0 12px; font-size: 28px; }}
    h2 {{ margin: 24px 0 10px; font-size: 18px; }}
    .panel {{ background: #fff; border: 1px solid #dfe3e8; border-radius: 8px; padding: 20px; margin: 16px 0; }}
    dl {{ display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 10px 16px; margin: 0; }}
    dt {{ font-weight: 700; }}
    dd {{ margin: 0; overflow-wrap: anywhere; }}
    pre {{ overflow: auto; background: #111827; color: #e5e7eb; padding: 16px; border-radius: 8px; }}
  </style>
</head>
<body><main>{body}</main></body>
</html>"""


class OAuth2AdapterHandler(BaseHTTPRequestHandler):
    server_version = "OAuth2Adapter/1.0"

    def do_GET(self):
        cleanup_expired()
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.handle_index()
        elif parsed.path == "/authorize":
            self.handle_authorize(parsed)
        elif parsed.path == "/callback":
            self.handle_callback(parsed)
        elif parsed.path == "/userinfo":
            self.handle_userinfo()
        elif parsed.path == "/resource":
            self.handle_resource()
        elif parsed.path == "/.well-known/oauth-authorization-server":
            self.write_json(self.metadata())
        elif parsed.path == "/health":
            self.write_text("ok\n")
        else:
            self.write_html(*render_page("Not Found", "<h1>404</h1>", HTTPStatus.NOT_FOUND))

    def do_POST(self):
        cleanup_expired()
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/token":
            self.handle_token()
        else:
            self.write_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")

    def write_text(self, body, status=HTTPStatus.OK):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def write_json(self, value, status=HTTPStatus.OK):
        data = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def write_html(self, status, body):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, location):
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.end_headers()

    def metadata(self):
        return {
            "issuer": PUBLIC_BASE,
            "authorization_endpoint": f"{PUBLIC_BASE}/authorize",
            "token_endpoint": f"{PUBLIC_BASE}/token",
            "userinfo_endpoint": f"{PUBLIC_BASE}/userinfo",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "token_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post",
            ],
            "scopes_supported": ["profile", "email"],
        }

    def handle_index(self):
        body = f"""
<h1>OAuth2 Adapter</h1>
<div class="panel">
  <dl>
    <dt>Public base</dt><dd>{html.escape(PUBLIC_BASE)}</dd>
    <dt>OAuth authorize</dt><dd>{html.escape(PUBLIC_BASE + "/authorize")}</dd>
    <dt>OAuth token</dt><dd>{html.escape(PUBLIC_BASE + "/token")}</dd>
    <dt>OAuth userinfo</dt><dd>{html.escape(PUBLIC_BASE + "/userinfo")}</dd>
    <dt>Downstream client</dt><dd>{html.escape(OAUTH2_CLIENT_ID)}</dd>
    <dt>Downstream redirect URI</dt><dd>{html.escape(OAUTH2_CLIENT_REDIRECT_URI)}</dd>
    <dt>Upstream SATOSA client</dt><dd>{html.escape(SATOSA_CLIENT_ID)}</dd>
    <dt>Upstream SATOSA scope</dt><dd>{html.escape(SATOSA_SCOPE)}</dd>
  </dl>
</div>
"""
        self.write_html(*render_page("OAuth2 Adapter", body))

    def handle_authorize(self, parsed):
        query = urllib.parse.parse_qs(parsed.query)
        client_id = first(query, "client_id")
        redirect_uri = first(query, "redirect_uri")
        response_type = first(query, "response_type")
        requested_scope = first(query, "scope")
        downstream_state = first(query, "state")

        client = CLIENTS.get(client_id)
        if not client or redirect_uri not in client["redirect_uris"]:
            self.write_json({"error": "invalid_client_or_redirect_uri"}, HTTPStatus.BAD_REQUEST)
            return
        if response_type != "code":
            self.redirect(
                redirect_error(
                    redirect_uri,
                    "unsupported_response_type",
                    downstream_state,
                    "Only authorization code flow is supported.",
                )
            )
            return

        adapter_state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        with STORE_LOCK:
            PENDING_AUTH[adapter_state] = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "state": downstream_state,
                "scope": requested_scope,
                "created_at": now(),
            }

        try:
            metadata = discovery()
        except Exception as exc:
            self.redirect(
                redirect_error(
                    redirect_uri,
                    "server_error",
                    downstream_state,
                    f"SATOSA discovery failed: {exc}",
                )
            )
            return

        upstream_params = {
            "client_id": SATOSA_CLIENT_ID,
            "redirect_uri": SATOSA_REDIRECT_URI,
            "response_type": "code",
            "scope": SATOSA_SCOPE,
            "state": adapter_state,
            "nonce": nonce,
        }
        self.redirect(add_query(metadata["authorization_endpoint"], upstream_params))

    def handle_callback(self, parsed):
        query = urllib.parse.parse_qs(parsed.query)
        adapter_state = first(query, "state")
        with STORE_LOCK:
            pending = PENDING_AUTH.pop(adapter_state, None)

        if not pending:
            self.write_json({"error": "invalid_state"}, HTTPStatus.BAD_REQUEST)
            return

        if "error" in query:
            self.redirect(
                redirect_error(
                    pending["redirect_uri"],
                    first(query, "error", "server_error"),
                    pending.get("state"),
                    first(query, "error_description"),
                )
            )
            return

        upstream_code = first(query, "code")
        if not upstream_code:
            self.redirect(
                redirect_error(
                    pending["redirect_uri"],
                    "server_error",
                    pending.get("state"),
                    "SATOSA callback did not include a code.",
                )
            )
            return

        try:
            metadata = discovery()
            upstream_token_response = self.exchange_satosa_code(
                metadata["token_endpoint"], upstream_code
            )
            userinfo = self.fetch_satosa_userinfo(
                metadata.get("userinfo_endpoint"),
                upstream_token_response.get("access_token"),
            )
        except Exception as exc:
            self.redirect(
                redirect_error(
                    pending["redirect_uri"],
                    "server_error",
                    pending.get("state"),
                    f"SATOSA token exchange failed: {exc}",
                )
            )
            return

        downstream_code = secrets.token_urlsafe(32)
        with STORE_LOCK:
            AUTHORIZATION_CODES[downstream_code] = {
                "client_id": pending["client_id"],
                "redirect_uri": pending["redirect_uri"],
                "scope": pending["scope"],
                "userinfo": userinfo,
                "satosa_token_response": upstream_token_response,
                "created_at": now(),
            }

        params = {"code": downstream_code}
        if pending.get("state"):
            params["state"] = pending["state"]
        self.redirect(add_query(pending["redirect_uri"], params))

    def exchange_satosa_code(self, token_endpoint, code):
        credentials = f"{SATOSA_CLIENT_ID}:{SATOSA_CLIENT_SECRET}".encode("utf-8")
        auth = base64.b64encode(credentials).decode("ascii")
        return json_request(
            token_endpoint,
            method="POST",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": SATOSA_REDIRECT_URI,
            },
            headers={"Authorization": f"Basic {auth}"},
        )

    def fetch_satosa_userinfo(self, endpoint, access_token):
        if not endpoint or not access_token:
            return {}
        return json_request(endpoint, bearer_token=access_token)

    def handle_token(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        form = urllib.parse.parse_qs(raw_body)

        client_id, client_secret = parse_basic_auth(self.headers.get("Authorization"))
        if not client_id:
            client_id = first(form, "client_id")
            client_secret = first(form, "client_secret")

        client = CLIENTS.get(client_id)
        if not client or client_secret != client["client_secret"]:
            self.write_json({"error": "invalid_client"}, HTTPStatus.UNAUTHORIZED)
            return

        if first(form, "grant_type") != "authorization_code":
            self.write_json({"error": "unsupported_grant_type"}, HTTPStatus.BAD_REQUEST)
            return

        code = first(form, "code")
        redirect_uri = first(form, "redirect_uri")
        with STORE_LOCK:
            code_record = AUTHORIZATION_CODES.pop(code, None)

        if not code_record:
            self.write_json({"error": "invalid_grant"}, HTTPStatus.BAD_REQUEST)
            return
        if code_record["client_id"] != client_id or code_record["redirect_uri"] != redirect_uri:
            self.write_json({"error": "invalid_grant"}, HTTPStatus.BAD_REQUEST)
            return

        access_token = secrets.token_urlsafe(40)
        with STORE_LOCK:
            ACCESS_TOKENS[access_token] = {
                "client_id": client_id,
                "scope": code_record.get("scope", ""),
                "userinfo": code_record.get("userinfo", {}),
                "satosa_token_response": code_record.get("satosa_token_response", {}),
                "created_at": now(),
            }

        self.write_json(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": ACCESS_TOKEN_TTL,
                "scope": code_record.get("scope", ""),
            }
        )

    def token_record_from_header(self):
        authorization = self.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return None
        token = authorization[7:].strip()
        with STORE_LOCK:
            record = ACCESS_TOKENS.get(token)
        if not record:
            return None
        if record["created_at"] + ACCESS_TOKEN_TTL < now():
            with STORE_LOCK:
                ACCESS_TOKENS.pop(token, None)
            return None
        return record

    def handle_userinfo(self):
        record = self.token_record_from_header()
        if not record:
            self.write_json({"error": "invalid_token"}, HTTPStatus.UNAUTHORIZED)
            return
        self.write_json(record.get("userinfo") or {})

    def handle_resource(self):
        record = self.token_record_from_header()
        if not record:
            self.write_json({"error": "invalid_token"}, HTTPStatus.UNAUTHORIZED)
            return
        self.write_json(
            {
                "message": "Protected resource reached with an OAuth2 access token.",
                "client_id": record.get("client_id"),
                "scope": record.get("scope"),
                "user": record.get("userinfo") or {},
            }
        )


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), OAuth2AdapterHandler)
    print(f"OAuth2 adapter listening on 0.0.0.0:{PORT}")
    print(f"Public base: {PUBLIC_BASE}")
    print(f"SATOSA redirect URI: {SATOSA_REDIRECT_URI}")
    server.serve_forever()
