# doomsday-device
yet another doomsday device
it will be (probably) python powered thermostat.

HW
DHT22 will be used for checking predefined temperature.
5V relay to start the boiler

SW
Python 3, will run in 5 minute interval - by cron
Adafruit library is required for DHT
JSON for storing config & temperature


in near future:
web app for simple update json
dunno, maybe more DHT22 or series of DS18B20 with logging (2 inside + 1 outside)
