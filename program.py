#!/usr/bin/python3

import crappyCode as magic

dry_run = False		# run without changing relay state
remote_log = True	# enable/disable remote logging
database_log = True	# enable/disable database Temp logging

# create object for logging
# def parameters are logPath = thermometer.log, size = 1048576 bytes (10MB), backup = 10 (files), level = INFO
log = magic.log()

# create object thermostat, it contain core function
# mandatory parameters -> variable with log object, default confPath = conf.json
therm = magic.thermostat(log)

# check if relay on boiler is in "right" state
if not dry_run:
	therm.checkBoiler()	#return true if state was changed

# log temp to database
# mandatory -> variable with termostat class, default dbPath = tempDB.sqlite3
if not database_log:
	db = magic.db(therm)
	db.insert()

# remote log
# mandatory -> variable with thermostat class
if not remote_log:
	remote = magic.remoteLog(therm)
	remote.upload()