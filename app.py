from flask import Flask, jsonify, render_template, request
from datetime import datetime, timezone
import logging
from sports_data import get_all_events
from fantasy_football_data import get_current_week_matchups

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)s: %(message)s")

app = Flask(__name__)

app.config["TICKER_MODE"] = "sports"

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

@app.route("/set_mode", methods=["POST"])
def set_mode():
    data = request.json
    mode = data.get("mode")
    if mode in ("sports", "fantasy"):
        app.config["TICKER_MODE"] = mode
        return {"status": "ok", "mode": mode}
    return {"status": "error", "message": "Invalid mode"}, 400


@app.route("/")
def index():
    mode = app.config["TICKER_MODE"]
    if mode == "sports":
        return render_template("index.html")
    elif mode == "fantasy":
        return render_template("fantasy.html")

@app.route("/data")
def data():
    mode = app.config["TICKER_MODE"]
    if mode == "sports":
        events, alert = get_all_events()
        return jsonify({
            "events": events,
            "alert": alert
        })
    elif mode == "fantasy":
        events = get_current_week_matchups()
        return jsonify({
            "events": events
        })
    else:
        return jsonify({"error": "Invalid mode"}), 400

if __name__ == "__main__":
    app.run(debug=True, port=5050)
