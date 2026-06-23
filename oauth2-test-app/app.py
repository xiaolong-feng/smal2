import base64
import html
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PORT = int(os.getenv("PORT", "8080"))
AUTHORIZATION_ENDPOINT = os.getenv(
    "OAUTH_AUTHORIZATION_ENDPOINT", "http://localhost:19090/authorize"
)
TOKEN_ENDPOINT = os.getenv("OAUTH_TOKEN_ENDPOINT", "http://oauth2-adapter:8080/token")
USERINFO_ENDPOINT = os.getenv(
    "OAUTH_USERINFO_ENDPOINT", "http://oauth2-adapter:8080/userinfo"
)
RESOURCE_ENDPOINT = os.getenv(
    "OAUTH_RESOURCE_ENDPOINT", "http://oauth2-adapter:8080/resource"
)
CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "oauth2-test-app")
CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "oauth-test-secret")
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:19091/callback")
SCOPE = os.getenv("OAUTH_SCOPE", "profile email")
COOKIE_NAME = "oauth2_test_state"


def json_request(url, method="GET", data=None, headers=None, bearer_token=None):
    headers = dict(headers or {})
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw)


def b64url_decode(value):
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


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
    body {{ margin: 0; padding: 32px; font-family: Arial, sans-serif; background: #f7f8fa; color: #202124; }}
    main {{ max-width: 1120px; margin: 0 auto; }}
    h1 {{ margin: 0 0 12px; font-size: 28px; }}
    h2 {{ margin: 24px 0 10px; font-size: 18px; }}
    .panel {{ background: #fff; border: 1px solid #dfe3e8; border-radius: 8px; padding: 20px; margin: 16px 0; }}
    .actions {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 18px 0 0; }}
    a.button {{ display: inline-flex; align-items: center; min-height: 40px; padding: 0 14px; border-radius: 6px; background: #1668dc; color: #fff; text-decoration: none; font-weight: 700; }}
    a.secondary {{ background: #5f6368; }}
    dl {{ display: grid; grid-template-columns: 210px minmax(0, 1fr); gap: 10px 16px; margin: 0; }}
    dt {{ font-weight: 700; }}
    dd {{ margin: 0; overflow-wrap: anywhere; }}
    pre {{ overflow: auto; background: #111827; color: #e5e7eb; padding: 16px; border-radius: 8px; }}
    .ok {{ color: #137333; font-weight: 700; }}
    .warn {{ color: #b06000; font-weight: 700; }}
    .error {{ color: #b3261e; font-weight: 700; }}
  </style>
</head>
<body><main>{body}</main></body>
</html>"""


class OAuth2TestHandler(BaseHTTPRequestHandler):
    server_version = "OAuth2TestApp/1.0"

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

    def make_state_cookie(self, state):
        payload = json.dumps({"state": state, "ts": int(time.time())}).encode("utf-8")
        encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
        return f"{COOKIE_NAME}={encoded}; Path=/; HttpOnly; SameSite=Lax; Max-Age=600"

    def clear_state_cookie(self):
        return f"{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"

    def handle_index(self):
        openid_warning = (
            '<span class="ok">No openid scope is sent by this application.</span>'
            if "openid" not in SCOPE.split()
            else '<span class="warn">The configured scope contains openid.</span>'
        )
        body = f"""
<h1>Pure OAuth2 Test App</h1>
<div class="panel">
  <p>This client only starts an OAuth2 authorization code flow against the adapter.</p>
  <dl>
    <dt>Authorization endpoint</dt><dd>{html.escape(AUTHORIZATION_ENDPOINT)}</dd>
    <dt>Token endpoint</dt><dd>{html.escape(TOKEN_ENDPOINT)}</dd>
    <dt>UserInfo endpoint</dt><dd>{html.escape(USERINFO_ENDPOINT)}</dd>
    <dt>Client ID</dt><dd>{html.escape(CLIENT_ID)}</dd>
    <dt>Redirect URI</dt><dd>{html.escape(REDIRECT_URI)}</dd>
    <dt>Requested scope</dt><dd>{html.escape(SCOPE)} {openid_warning}</dd>
  </dl>
  <div class="actions">
    <a class="button" href="/login">Start OAuth2 Login</a>
  </div>
</div>
"""
        self.write_html(*render_page("Pure OAuth2 Test App", body))

    def handle_login(self):
        state = secrets.token_urlsafe(24)
        params = {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPE,
            "state": state,
        }
        location = f"{AUTHORIZATION_ENDPOINT}?{urllib.parse.urlencode(params)}"
        self.redirect(location, [self.make_state_cookie(state)])

    def handle_callback(self, parsed):
        query = urllib.parse.parse_qs(parsed.query)
        if "error" in query:
            self.write_error("OAuth2 login failed", {"callback_query": query})
            return

        code = query.get("code", [""])[0]
        returned_state = query.get("state", [""])[0]
        cookie_state = self.read_state_cookie()
        if not code:
            self.write_error("Callback did not include code", {"callback_query": query})
            return
        if not cookie_state or returned_state != cookie_state.get("state"):
            self.write_error("State validation failed", {"callback_query": query})
            return

        try:
            token_response = self.exchange_code(code)
            access_token = token_response.get("access_token")
            userinfo = json_request(USERINFO_ENDPOINT, bearer_token=access_token)
            resource = json_request(RESOURCE_ENDPOINT, bearer_token=access_token)
        except Exception as exc:
            self.write_error("Token or resource request failed", self.error_detail(exc))
            return

        body = f"""
<h1>OAuth2 Login Success</h1>
<div class="panel">
  <dl>
    <dt>code</dt><dd>{html.escape(code[:32])}...</dd>
    <dt>access_token</dt><dd>{html.escape(str(access_token or '')[:48])}...</dd>
    <dt>token_type</dt><dd>{html.escape(str(token_response.get('token_type', '')))}</dd>
    <dt>id_token present</dt><dd class="ok">{html.escape(str('id_token' in token_response))}</dd>
    <dt>scope requested</dt><dd>{html.escape(SCOPE)}</dd>
    <dt>sub</dt><dd>{html.escape(str(userinfo.get('sub', '')))}</dd>
    <dt>email</dt><dd>{html.escape(str(userinfo.get('email', '')))}</dd>
    <dt>name</dt><dd>{html.escape(str(userinfo.get('name', '')))}</dd>
  </dl>
  <div class="actions"><a class="button secondary" href="/">Back</a></div>
</div>

<h2>Token Response</h2>
<pre>{render_json(token_response)}</pre>

<h2>UserInfo</h2>
<pre>{render_json(userinfo)}</pre>

<h2>Protected Resource</h2>
<pre>{render_json(resource)}</pre>
"""
        self.write_html(*render_page("OAuth2 Login Success", body), cookies=[self.clear_state_cookie()])

    def exchange_code(self, code):
        credentials = f"{CLIENT_ID}:{CLIENT_SECRET}".encode("utf-8")
        auth = base64.b64encode(credentials).decode("ascii")
        return json_request(
            TOKEN_ENDPOINT,
            method="POST",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
            headers={"Authorization": f"Basic {auth}"},
        )

    def error_detail(self, exc):
        detail = {"type": exc.__class__.__name__, "message": str(exc)}
        if isinstance(exc, urllib.error.HTTPError):
            detail["status"] = exc.code
            try:
                detail["response_body"] = exc.read().decode("utf-8")
            except Exception:
                pass
        return detail

    def write_error(self, title, detail):
        body = f"""
<h1>{html.escape(title)}</h1>
<div class="panel">
  <pre>{render_json(detail)}</pre>
  <div class="actions"><a class="button secondary" href="/">Back</a></div>
</div>
"""
        self.write_html(*render_page(title, body, HTTPStatus.INTERNAL_SERVER_ERROR))


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), OAuth2TestHandler)
    print(f"OAuth2 test app listening on 0.0.0.0:{PORT}")
    print(f"Authorization endpoint: {AUTHORIZATION_ENDPOINT}")
    print(f"Requested scope: {SCOPE}")
    server.serve_forever()
