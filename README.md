APsystems to InfluxDB
=====================

This script pulls data from the APsystems cloud and pushes it to an InfluxDB 1.0
database.

Inspired by https://github.com/bgbraga/homeassistant-apsystems.

## APsystems Connection

This pulls from
`https://apsystemsema.com/ema/ajax/getReportApiAjax/getPowerOnCurrentDayAjax`.
It collects 5 minute interval power and energy data for the current day.

## Configuration

This requires two configurations: one for the APsystems system and one for the
InfluxDB database.

### APsystems Configuration

`/etc/swarm-gateway/apsystems.conf`:

```
username=
password=
system_id=
ecu_id=
location_general=
```

Use your apsystemsema.com user to configure the configuration.yaml.

1. Your System ID is found at apsystemsema.com. View the page source code and in
   the Settings Menu there is a code that looks like:

    ```html
    <span>Settings</span>
    <ul>
        <li onclick="managementClickCustomer('YOUR SYSTEM ID')"><a>Settings</a></li>
        <li onclick="intoFaq(10)"><a>Help</a></li>
    </ul>
    ```
    Get the system id inside the `managementClickCustomer()`.

2. The ECU ID is at
   `https://apsystemsema.com/ema/security/optmainmenu/intoLargeReport.action`.


### InfluxDB Configuration

`/etc/swarm-gateway/influx.conf`

```
url=
port=
username=
password=
database=
```
