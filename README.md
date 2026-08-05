# pskreporter-local

A local-first web interface for exploring recent amateur-radio reception reports from the documented [PSK Reporter XML query interface](https://www.pskreporter.info/pskdev.html).

## Project direction

Development will proceed in small, working increments:

1. Display recent PSK Reporter results in a responsive HTML table.
2. Plot the same normalized reports on a responsive world map.
3. Add local ADIF log integration and worked-before indicators.

UDP integrations and external callsign lookup services are intentionally outside the initial scope.

## First milestone

Enter a transmitting callsign and display its recent reception reports with:

- UTC report time
- transmitting and receiving callsigns
- receiver Maidenhead locator
- frequency and derived amateur band
- mode, when supplied
- report age and data freshness

The local service will parse PSK Reporter's XML, expose normalized JSON to the browser, and cache equivalent queries for at least five minutes in accordance with the service's published polling guidance.

## Status

Project setup and planning. No application release is available yet.

## License

MIT
