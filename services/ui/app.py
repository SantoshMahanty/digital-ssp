from flask import Flask, render_template, request
import httpx
import os

API_BASE = "http://localhost:8001"
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)


def fetch_debug(req_id: str):
  try:
    resp = httpx.get(f"{API_BASE}/debug/{req_id}", timeout=2.0)
    if resp.status_code == 200:
      return resp.json()
  except Exception:
    return None
  return None


@app.route("/")
def index():
  return """
  <h2>GAM 360 Simulator - Flask UI</h2>
  <ul>
    <li><a href="/inventory">Inventory</a></li>
    <li><a href="/orders">Orders</a></li>
    <li><a href="/yield">Yield</a></li>
    <li><a href="/reports">Reports</a></li>
    <li><a href="/inspector">Inspector</a></li>
  </ul>
  """


@app.route("/inventory")
def inventory():
  return """
  <h2>Inventory</h2>
  <table border="1">
    <tr><th>Code</th><th>Sizes</th><th>Placements</th></tr>
    <tr><td>news/home</td><td>970x250,300x250</td><td>homepage</td></tr>
    <tr><td>news/article/top</td><td>728x90,300x250</td><td>article</td></tr>
  </table>
  """


@app.route("/orders")
def orders():
  return """
  <h2>Orders</h2>
  <table border="1">
    <tr><th>Name</th><th>Status</th><th>Line Items</th></tr>
    <tr><td>Brand A Q1</td><td>Running</td><td>5</td></tr>
    <tr><td>Brand B Burst</td><td>Pending</td><td>3</td></tr>
  </table>
  """


@app.route("/yield")
def yield_view():
  return """
  <h2>Yield Management</h2>
  <h3>Unified Floors</h3>
  <table border="1">
    <tr><th>Context</th><th>Floor</th></tr>
    <tr><td>US / desktop / display</td><td>$1.20</td></tr>
    <tr><td>EU / mobile / display</td><td>$0.80</td></tr>
  </table>
  """


@app.route("/reports")
def reports():
  return """
  <h2>Reports</h2>
  <table border="1">
    <tr><th>Hour</th><th>Requests</th><th>Impressions</th><th>eCPM</th></tr>
    <tr><td>10:00</td><td>120,000</td><td>86,000</td><td>$3.43</td></tr>
    <tr><td>11:00</td><td>118,000</td><td>84,500</td><td>$3.41</td></tr>
  </table>
  """


@app.route("/inspector", methods=["GET"])
def inspector():
  req_id = request.args.get("reqId")
  trace = fetch_debug(req_id) if req_id else None
  trace_html = "<li>No trace loaded</li>"
  if trace:
    trace_html = f"<li>Trace for {req_id}: {trace}</li>"
  return f"""
  <h2>Ad Inspector</h2>
  <form method="get">
    <label>Request ID: <input name="reqId" value="{req_id or ''}" /></label>
    <button type="submit">Fetch</button>
  </form>
  <ul>
    {trace_html}
  </ul>
  """


@app.errorhandler(500)
def internal_error(error):
  import traceback
  tb = traceback.format_exc()
  return f"<h1>500 Internal Error</h1><pre>{tb}</pre>", 500


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=3000, debug=True)
