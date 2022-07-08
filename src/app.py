from functools import lru_cache
import json
import math
import sys
import time

from flask import Flask, jsonify
import requests

from .jils import JILSClient

app = Flask(__name__, static_url_path='/static')
jils = JILSClient()


@app.route("/")
def home():
    return app.send_static_file("index.html")

  
@app.route("/poll")
def poll_jils():
    records = lookup_jils(math.floor(time.time() / 60))
    return jsonify(records)


# Limit requests to 1 per minute
@lru_cache(maxsize=1)
def lookup_jils(seconds):
    return jils.list_bookings_in_last_24_hours()


if __name__ == "__main__":
    app.run()