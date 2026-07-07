import base64
import html
import json
import os
import secrets
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


ISSUER = os.getenv("OIDC_ISSUER", "https://202.122.38.207:8443").rstrip("/")
DISCOVERY_URL = os.getenv(
    "OIDC_DISCOVERY_URL", f"{ISSUER}/.well-known/openid-configuration"
)
CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "oidc-test-app")
CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "test-secret")
REDIRECT_URI = os.getenv("OIDC_REDIRECT_URI", "http://202.122.38.207:18080/callback")
SCOPE = os.getenv("OIDC_SCOPE", "openid profile email")
PORT = int(os.getenv("PORT", "8080"))
VERIFY_TLS = os.getenv("OIDC_VERIFY_TLS", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

AUTHORIZATION_ENDPOINT = os.getenv("OIDC_AUTHORIZATION_ENDPOINT")
TOKEN_ENDPOINT = os.getenv("OIDC_TOKEN_ENDPOINT")
USERINFO_ENDPOINT = os.getenv("OIDC_USERINFO_ENDPOINT")

COOKIE_NAME = "oidc_test_state"


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
    metadata = json_request(DISCOVERY_URL)
    return {
        "issuer": metadata.get("issuer", ISSUER),
        "authorization_endpoint": AUTHORIZATION_ENDPOINT
        or metadata["authorization_endpoint"],
        "token_endpoint": TOKEN_ENDPOINT or metadata["token_endpoint"],
        "userinfo_endpoint": USERINFO_ENDPOINT or metadata.get("userinfo_endpoint"),
        "raw": metadata,
        "discovery_url": DISCOVERY_URL,
    }


def b64url_decode(value):
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def decode_jwt_without_verification(token):
    if not token or token.count(".") != 2:
        return None
    header_b64, payload_b64, _signature_b64 = token.split(".")
    return {
        "header": json.loads(b64url_decode(header_b64)),
        "claims": json.loads(b64url_decode(payload_b64)),
    }


def render_json(value):
    return html.escape(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def render_page(title, body, status=HTTPStatus.OK):
    return status, f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Arial, sans-serif;
      color: #202124;
      background: #f7f8fa;
    }}
    body {{
      margin: 0;
      padding: 32px;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 28px;
      font-weight: 700;
    }}
    h2 {{
      margin: 24px 0 10px;
      font-size: 18px;
    }}
    p {{
      line-height: 1.6;
    }}
    .panel {{
      background: #fff;
      border: 1px solid #dfe3e8;
      border-radius: 8px;
      padding: 20px;
      margin: 16px 0;
    }}
    .actions {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin: 18px 0 0;
    }}
    a.button {{
      display: inline-flex;
      align-items: center;
      min-height: 40px;
      padding: 0 14px;
      border-radius: 6px;
      background: #1668dc;
      color: #fff;
      text-decoration: none;
      font-weight: 700;
    }}
    a.secondary {{
      background: #5f6368;
    }}
    dl {{
      display: grid;
      grid-template-columns: 180px minmax(0, 1fr);
      gap: 10px 16px;
      margin: 0;
    }}
    dt {{
      font-weight: 700;
      color: #3c4043;
    }}
    dd {{
      margin: 0;
      overflow-wrap: anywhere;
    }}
    pre {{
      overflow: auto;
      background: #111827;
      color: #e5e7eb;
      padding: 16px;
      border-radius: 8px;
      line-height: 1.45;
      font-size: 13px;
    }}
    .ok {{
      color: #137333;
      font-weight: 700;
    }}
    .warn {{
      color: #b06000;
      font-weight: 700;
    }}
    .error {{
      color: #b3261e;
      font-weight: 700;
    }}
  </style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>"""


class OIDCTestHandler(BaseHTTPRequestHandler):
    server_version = "OIDCTestApp/1.0"

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.handle_index()
        elif parsed.path == "/login":
            self.handle_login()
        elif parsed.path == "/callback":
            self.handle_callback(parsed)
        elif parsed.path == "/health":
            self.write_text("ok\n")
        else:
            self.write_html(*render_page("Not Found", "<h1>404</h1>", HTTPStatus.NOT_FOUND))

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")

    def write_text(self, body, status=HTTPStatus.OK):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def write_html(self, status, body, cookies=None):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        if cookies:
            for cookie in cookies:
                self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, location, cookies=None):
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        if cookies:
            for cookie in cookies:
                self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def read_state_cookie(self):
        cookie_header = self.headers.get("Cookie", "")
        for item in cookie_header.split(";"):
            name, _, value = item.strip().partition("=")
            if name == COOKIE_NAME:
                try:
                    return json.loads(b64url_decode(value).decode("utf-8"))
                except Exception:
                    return None
        return None

    def make_state_cookie(self, state, nonce):
        payload = json.dumps(
            {"state": state, "nonce": nonce, "ts": int(time.time())}
        ).encode("utf-8")
        encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
        return f"{COOKIE_NAME}={encoded}; Path=/; HttpOnly; SameSite=Lax; Max-Age=600"

    def clear_state_cookie(self):
        return f"{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"

    def handle_index(self):
        body = f"""
<h1>OIDC Test App</h1>
<div class="panel">
  <p>This app verifies that an OIDC client can log in through SATOSA and fetch user claims without writing local user records.</p>
  <dl>
    <dt>Issuer</dt><dd>{html.escape(ISSUER)}</dd>
    <dt>Discovery URL</dt><dd>{html.escape(DISCOVERY_URL)}</dd>
    <dt>Client ID</dt><dd>{html.escape(CLIENT_ID)}</dd>
    <dt>Redirect URI</dt><dd>{html.escape(REDIRECT_URI)}</dd>
    <dt>Scope</dt><dd>{html.escape(SCOPE)}</dd>
    <dt>TLS Verify</dt><dd>{html.escape(str(VERIFY_TLS))}</dd>
  </dl>
  <div class="actions">
    <a class="button" href="/login">Start OIDC Login</a>
  </div>
</div>
"""
        self.write_html(*render_page("OIDC Test App", body))

    def handle_login(self):
        try:
            metadata = discovery()
        except Exception as exc:
            self.write_error("Discovery failed", exc)
            return

        state = secrets.token_urlsafe(24)
        nonce = secrets.token_urlsafe(24)
        params = {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPE,
            "state": state,
            "nonce": nonce,
        }
        location = f"{metadata['authorization_endpoint']}?{urllib.parse.urlencode(params)}"
        self.redirect(location, [self.make_state_cookie(state, nonce)])

    def handle_callback(self, parsed):
        query = urllib.parse.parse_qs(parsed.query)
        if "error" in query:
            body = f"""
<h1>Login Failed</h1>
<div class="panel">
  <p class="error">{html.escape(query.get("error", [""])[0])}</p>
  <pre>{render_json(query)}</pre>
  <div class="actions"><a class="button secondary" href="/">Back</a></div>
</div>
"""
            self.write_html(
                *render_page("Login Error", body), cookies=[self.clear_state_cookie()]
            )
            return

        code = query.get("code", [""])[0]
        returned_state = query.get("state", [""])[0]
        cookie_state = self.read_state_cookie()
        if not code:
            self.write_error(
                "Callback missing code",
                ValueError("OIDC callback did not include an authorization code"),
            )
            return
        if not cookie_state or returned_state != cookie_state.get("state"):
            self.write_error(
                "State validation failed",
                ValueError("Callback state does not match the login session"),
            )
            return

        try:
            metadata = discovery()
            token_response = self.exchange_code(metadata["token_endpoint"], code)
            id_token = token_response.get("id_token")
            decoded_id_token = decode_jwt_without_verification(id_token)
            userinfo = self.fetch_userinfo(
                metadata.get("userinfo_endpoint"), token_response.get("access_token")
            )
        except Exception as exc:
            self.write_error("Token or userinfo request failed", exc)
            return

        id_claims = decoded_id_token.get("claims") if decoded_id_token else {}
        userinfo_sub = userinfo.get("sub") if isinstance(userinfo, dict) else None
        sub_match = bool(
            id_claims.get("sub") and userinfo_sub and id_claims.get("sub") == userinfo_sub
        )
        sub_status = "match" if sub_match else "not confirmed"
        sub_class = "ok" if sub_match else "warn"

        body = f"""
<h1>Login Success</h1>
<div class="panel">
  <dl>
    <dt>code</dt><dd>{html.escape(code[:32])}...</dd>
    <dt>id_token.sub</dt><dd>{html.escape(str(id_claims.get("sub", "")))}</dd>
    <dt>userinfo.sub</dt><dd>{html.escape(str(userinfo_sub or ""))}</dd>
    <dt>sub check</dt><dd class="{sub_class}">{sub_status}</dd>
    <dt>email</dt><dd>{html.escape(str(id_claims.get("email") or (userinfo or {}).get("email") or ""))}</dd>
    <dt>name</dt><dd>{html.escape(str(id_claims.get("name") or (userinfo or {}).get("name") or ""))}</dd>
    <dt>preferred_username</dt><dd>{html.escape(str(id_claims.get("preferred_username") or (userinfo or {}).get("preferred_username") or ""))}</dd>
  </dl>
  <div class="actions">
    <a class="button secondary" href="/">Back</a>
  </div>
</div>

<h2>ID Token Claims</h2>
<pre>{render_json(id_claims)}</pre>

<h2>UserInfo</h2>
<pre>{render_json(userinfo)}</pre>

<h2>Token Response</h2>
<pre>{render_json(token_response)}</pre>

<h2>Discovery Metadata</h2>
<pre>{render_json(metadata["raw"])}</pre>
"""
        self.write_html(
            *render_page("Login Success", body), cookies=[self.clear_state_cookie()]
        )

    def exchange_code(self, token_endpoint, code):
        credentials = f"{CLIENT_ID}:{CLIENT_SECRET}".encode("utf-8")
        auth = base64.b64encode(credentials).decode("ascii")
        return json_request(
            token_endpoint,
            method="POST",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
            headers={"Authorization": f"Basic {auth}"},
        )

    def fetch_userinfo(self, endpoint, access_token):
        if not endpoint:
            return {"warning": "Provider discovery metadata did not include a userinfo_endpoint"}
        if not access_token:
            return {"warning": "Token response did not include an access_token"}
        return json_request(endpoint, bearer_token=access_token)

    def write_error(self, title, exc):
        detail = {
            "type": exc.__class__.__name__,
            "message": str(exc),
        }
        if isinstance(exc, urllib.error.HTTPError):
            try:
                detail["response_body"] = exc.read().decode("utf-8")
            except Exception:
                pass
            detail["status"] = exc.code

        body = f"""
<h1>{html.escape(title)}</h1>
<div class="panel">
  <p class="error">{html.escape(str(exc))}</p>
  <pre>{render_json(detail)}</pre>
  <div class="actions"><a class="button secondary" href="/">Back</a></div>
</div>
"""
        self.write_html(*render_page(title, body, HTTPStatus.INTERNAL_SERVER_ERROR))


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), OIDCTestHandler)
    print(f"OIDC test app listening on 0.0.0.0:{PORT}")
    print(f"OIDC issuer: {ISSUER}")
    print(f"Redirect URI: {REDIRECT_URI}")
    server.serve_forever()
