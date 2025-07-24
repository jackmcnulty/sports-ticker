# app.py

from flask import Flask, jsonify, render_template
from datetime import datetime, timezone
import logging
from sports_data import get_all_events

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)s: %(message)s")

app = Flask(__name__)

startup_time = datetime.now(timezone.utc).isoformat()

@app.route("/version")
def version():
    return {"startup": startup_time}

@app.after_request
def add_header(resp):
    if resp.cache_control.max_age is not None:
        resp.cache_control.max_age = 0
        resp.cache_control.no_store = True
        resp.headers['Pragma'] = 'no-cache'
        resp.expires = -1
    return resp

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data")
def data():
    events, alert = get_all_events()
    return jsonify(events=events, alert=alert)

if __name__ == "__main__":
    app.run(debug=True, port=5050)
