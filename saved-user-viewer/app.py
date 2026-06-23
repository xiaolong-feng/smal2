import html
import json
import os
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PORT = int(os.getenv("PORT", "8080"))
SAVED_USER_ATTRIBUTES_PATH = os.getenv(
    "SAVED_USER_ATTRIBUTES_PATH", "/opt/satosa/data/user_attributes.jsonl"
)
REQUESTER_FILTER = os.getenv(
    "REQUESTER_FILTER", "https://indico3-ldap.ihep.ac.cn/shibboleth"
)
PAGE_TITLE = os.getenv("PAGE_TITLE", "Indico SAML 保存的用户信息")
MAX_RECORDS = int(os.getenv("MAX_RECORDS", "20"))


def render_json(value):
    return html.escape(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def render_attribute_value(value):
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def deep_get(value, path):
    current = value
    for item in path:
        if not isinstance(current, dict):
            return None
        current = current.get(item)
    return current


def get_record_requester(record):
    candidates = [
        record.get("requester"),
        deep_get(record, ("data", "requester")),
        deep_get(record, ("data", "requester_entity_id")),
        deep_get(record, ("context", "state", "SATOSA_BASE", "requester")),
        deep_get(record, ("context", "state", "requester")),
    ]
    for candidate in candidates:
        if candidate:
            return str(candidate)
    return ""


def read_saved_records():
    if not os.path.exists(SAVED_USER_ATTRIBUTES_PATH):
        return [], None

    records = []
    errors = []
    try:
        with open(SAVED_USER_ATTRIBUTES_PATH, encoding="utf-8") as saved_file:
            for line_number, line in enumerate(saved_file, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    record["_line_number"] = line_number
                    record["_requester"] = get_record_requester(record)
                    records.append(record)
                except json.JSONDecodeError as exc:
                    errors.append("line {0}: {1}".format(line_number, exc))
    except OSError as exc:
        return [], str(exc)

    return list(reversed(records)), "; ".join(errors) if errors else None


def filter_records(records, include_all=False):
    if include_all or not REQUESTER_FILTER:
        return records
    return [
        record
        for record in records
        if REQUESTER_FILTER in (record.get("_requester") or "")
    ]


def render_records(records, include_all=False):
    if not records:
        if include_all or not REQUESTER_FILTER:
            message = "还没有读取到保存记录。完成一次登录后，这里会显示 SATOSA 落盘的用户信息。"
        else:
            message = "还没有读取到 Indico 的保存记录。请先通过 Indico 发起一次 SAML 登录。"
        return '<p class="warn">{0}</p>'.format(html.escape(message))

    latest = records[0]
    attributes = latest.get("attributes") or {}
    if attributes:
        attribute_rows = "\n".join(
            "<tr><th>{0}</th><td>{1}</td></tr>".format(
                html.escape(str(name)),
                html.escape(render_attribute_value(value)),
            )
            for name, value in sorted(attributes.items())
        )
        attributes_html = """
<table class="attributes-table">
  <tbody>
{rows}
  </tbody>
</table>
""".format(rows=attribute_rows)
    else:
        attributes_html = '<p class="warn">保存记录里没有 attributes 字段。</p>'

    recent_items = "\n".join(
        "<li><span>{time}</span><code>{requester}</code></li>".format(
            time=html.escape(str(record.get("saved_at", ""))),
            requester=html.escape(record.get("_requester") or "unknown requester"),
        )
        for record in records[:MAX_RECORDS]
    )

    return """
<dl>
  <dt>保存时间</dt><dd>{saved_at}</dd>
  <dt>SP / Requester</dt><dd>{requester}</dd>
  <dt>保存服务</dt><dd>{service}</dd>
  <dt>记录文件</dt><dd>{path}</dd>
</dl>

{attributes_html}

<h2>最近记录</h2>
<ul class="record-list">
{recent_items}
</ul>

<h2>最近保存记录 Raw JSON</h2>
<pre>{raw_json}</pre>
""".format(
        saved_at=html.escape(str(latest.get("saved_at", ""))),
        requester=html.escape(latest.get("_requester") or ""),
        service=html.escape(str(latest.get("service", ""))),
        path=html.escape(SAVED_USER_ATTRIBUTES_PATH),
        attributes_html=attributes_html,
        recent_items=recent_items,
        raw_json=render_json(latest),
    )


def render_page(body, status=HTTPStatus.OK):
    return status, """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Arial, "Microsoft YaHei", sans-serif;
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
    .attributes-table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 18px;
      table-layout: fixed;
    }}
    .attributes-table th,
    .attributes-table td {{
      border-top: 1px solid #e8eaed;
      padding: 10px 8px;
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }}
    .attributes-table th {{
      width: 220px;
      color: #3c4043;
      font-weight: 700;
    }}
    .record-list {{
      margin: 0;
      padding-left: 20px;
    }}
    .record-list li {{
      margin: 8px 0;
      overflow-wrap: anywhere;
    }}
    .record-list span {{
      display: inline-block;
      min-width: 230px;
      color: #5f6368;
    }}
    code {{
      font-family: Consolas, "Courier New", monospace;
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
</html>""".format(title=html.escape(PAGE_TITLE), body=body)


class SavedUserViewerHandler(BaseHTTPRequestHandler):
    server_version = "SavedUserViewer/1.0"

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            self.write_text("ok\n")
            return
        if parsed.path not in {"/", "/all"}:
            self.write_html(*render_page("<h1>404</h1>", HTTPStatus.NOT_FOUND))
            return

        include_all = parsed.path == "/all"
        records, error = read_saved_records()
        visible_records = filter_records(records, include_all=include_all)

        error_html = (
            '<p class="error">读取保存记录时出现错误：{0}</p>'.format(
                html.escape(error)
            )
            if error
            else ""
        )
        filter_html = (
            """
<dl>
  <dt>当前过滤</dt><dd>{requester}</dd>
</dl>
""".format(requester=html.escape(REQUESTER_FILTER))
            if REQUESTER_FILTER and not include_all
            else ""
        )

        body = """
<h1>{title}</h1>
<div class="panel">
  <p>这里展示 SATOSA 在 SAML/Indico 登录流程中保存到本地的用户信息。</p>
{filter_html}
  <div class="actions">
    <a class="button" href="/">刷新</a>
    <a class="button secondary" href="/all">查看全部记录</a>
  </div>
</div>
<div class="panel">
{error_html}
{records_html}
</div>
""".format(
            title=html.escape(PAGE_TITLE),
            filter_html=filter_html,
            error_html=error_html,
            records_html=render_records(visible_records, include_all=include_all),
        )
        self.write_html(*render_page(body))

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")

    def write_text(self, body, status=HTTPStatus.OK):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
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


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), SavedUserViewerHandler)
    print(f"Saved user viewer listening on 0.0.0.0:{PORT}")
    print(f"Reading saved users from: {SAVED_USER_ATTRIBUTES_PATH}")
    if REQUESTER_FILTER:
        print(f"Requester filter: {REQUESTER_FILTER}")
    server.serve_forever()
