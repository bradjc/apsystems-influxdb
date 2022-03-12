#!/usr/bin/env python3

from dateutil import tz
import datetime

import arrow
import influxdb
import mechanize
import requests
import sys


CONFIG_FILE_PATH = "/etc/swarm-gateway/apsystems.conf"
INFLUX_CONFIG_FILE_PATH = "/etc/swarm-gateway/influx.conf"

# Get AP systems config.
ap_config = {}
with open(CONFIG_FILE_PATH) as f:
    for l in f:
        fields = l.split("=")
        if len(fields) == 2:
            ap_config[fields[0].strip()] = fields[1].strip()

# Get influxDB config.
influx_config = {}
with open(INFLUX_CONFIG_FILE_PATH) as f:
    for l in f:
        fields = l.split("=")
        if len(fields) == 2:
            influx_config[fields[0].strip()] = fields[1].strip()


# Main logic for downloading a daily report from the APsystems cloud.
class APsystemsFetcher:
    url_login = "https://apsystemsema.com/ema/index.action"
    url_data = (
        "https://apsystemsema.com/ema/ajax/getReportApiAjax/getPowerOnCurrentDayAjax"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0"
    }

    def __init__(self, username, password, system_id, ecu_id):
        self._username = username
        self._password = password
        self._system_id = system_id
        self._ecu_id = ecu_id

    def login(self):
        browser = mechanize.Browser()
        browser.open(self.url_login)
        browser.select_form(nr=0)
        browser.form.set_all_readonly(False)
        browser.form["username"] = self._username
        browser.form["password"] = self._password
        browser.submit()

        return browser

    def fetch(self, day):
        browser = self.login()

        post_data = {
            "queryDate": day.strftime("%Y%m%d"),
            "selectedValue": self._ecu_id,
            "systemId": self._system_id,
        }

        session = requests.sessions.session()
        result_data = session.request(
            "POST",
            self.url_data,
            None,
            post_data,
            self.headers,
            browser.cookiejar,
        )

        if result_data.status_code == 204:
            print("204??")
            return None
        else:
            print("got json")
            return result_data.json()


# Data fetcher
fetcher = APsystemsFetcher(
    ap_config["username"],
    ap_config["password"],
    ap_config["system_id"],
    ap_config["ecu_id"],
)

# What day to fetch for. The API just takes a day and gives all readings for
# that day.
fetch_day = datetime.datetime.today() - datetime.timedelta(0)

# Get the day's data.
d = fetcher.fetch(fetch_day)

# Check if something went wrong.
if d == None:
    print("could not get ap systems data")
    sys.exit(-1)

# List of points to send to influxdb.
points = []

# Metadata added to each point.
metadata = {
    "device_id": "apsystems-ecu-{}".format(ap_config["ecu_id"]),
    "apsystems_system_id": ap_config["system_id"],
    "location_general": ap_config["location_general"],
    "location_specific": "Roof",
    "description": "Solar Panels",
}

# Format the solar data in the influx format I want.
for i in range(0, len(d["time"])):
    uts = d["time"][i]
    power = int(d["power"][i])
    energy = float(d["energy"][i])

    # Seems like AP systems is 8 hours behind me? This is confusing.
    uts += 8 * 60 * 60 * 1000

    # Need to convert the unix timestamp to UTC.
    t = arrow.get(uts).replace(tzinfo="US/Eastern").to("utc")
    # Need nanosecond timestamp for influx.
    ts = int(t.timestamp() * 1000 * 1000 * 1000)

    # Get a single measurement with the fields.
    point = {
        "measurement": "apsystems",
        "fields": {
            "power_w": power,
            "energy_kWh": energy,
        },
        "tags": metadata,
        "time": ts,
    }
    points.append(point)

    # Just power, in the generic-gateway format.
    point = {
        "measurement": "power_w",
        "fields": {
            "value": float(power),
        },
        "tags": metadata,
        "time": ts,
    }
    points.append(point)

    # Just energy, in the generic-gateway format.
    point = {
        "measurement": "energy_kWh",
        "fields": {
            "value": energy,
        },
        "tags": metadata,
        "time": ts,
    }
    points.append(point)

print("got points")


client = influxdb.InfluxDBClient(
    influx_config["url"],
    influx_config["port"],
    influx_config["username"],
    influx_config["password"],
    influx_config["database"],
    ssl=True,
    gzip=True,
    verify_ssl=True,
)


client.write_points(points)

print("wrote points")
