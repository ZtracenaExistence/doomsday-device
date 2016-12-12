#!/usr/bin/python3

import json, logging, logging.handlers, os, datetime, sqlite3
import RPi.GPIO as GPIO
import Adafruit_DHT as DHT
from urllib import request, parse

class thermostat:
	'welp, just another crappy documented code'
	#here you can place vars shared between same class
	
	def __init__(self, log, confPath = "conf.json"):
		self.log = log # set log object as variable accesible by whole class
		
		self.conf = self.loadConfig(os.path.join(os.path.dirname(os.path.abspath(__file__)), confPath))
		self.setGPIO()
		self.sensor = self.conf["sensor"]
		self.directive = self.currentDirective()
		self.targetTemp = self.targetTemp()
		self.currentTemp = self.readDHT() #tuple (temp, humidity)
   
	def loadConfig(self, confPath):
		try:
			with open(confPath) as file:
				read = file.read()
			return json.loads(read)
		except (PermissionError, FileNotFoundError) as e:
			self.log.write.critical('Thermostat can\'t load confing file:"{0}" - with error {1}, aborting script...'.format(confPath, e))
			self.forceQuit(False)
	
	def setGPIO(self):
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False) #well i'dont like it either, but for using GPIO with CRON is this best option
		self.log.write.debug("Setting pin {0} as output for relay".format(self.conf["relay"]))
		GPIO.setup(self.conf["relay"], GPIO.OUT)
		
	def forceQuit(self, conf = True):
		if conf == True:
			GPIO.output(self.conf['relay'], False) # just to be sure, turn off relay, cuz this function should't be called if there is no error
			GPIO.cleanup()
			self.log.write.critical('forceQuit function called, GPIO cleaned up...')
		else:
			self.log.write.critical('forceQuit function called without GPIO cleanup')
		exit()
		
	def currentDirective(self):
		if self.conf["manual"]["active"] != True:				#check for manual directive - cuz it have higher priority than pre programmed temperatures
			if datetime.datetime.today().weekday() < 5:		#if manual is false then check if its week
				return self.conf["week"]
			else:											#or weekend
				return self.conf["weekend"]
		else:
			return { "manual" : self.conf["manual"]["temp"] }
			
	def targetTemp(self):
		hours = sorted(list(self.directive.keys()))	#from self.directive (dict) take keys as sorted list
		now = datetime.datetime.now().time().strftime("%H:%M")
		
		needle = [ h for h in hours if h <= now ] # list all directives with lower timestamp than current time
		if not needle:		# if there is no directive with lower timestamp than "now", take timestamp with the highest value (like if now is 0:00 then last directive should be 23:59)
			needle.append(hours[-1])
		return self.directive[needle[-1]] # return last element from list where each element should have smaller value than current timestamp
		
	def readDHT(self):
		if self.conf["sensor"]["type"] == "DHT22":
			s = DHT.DHT22
		elif self.conf["sensor"]["type"] == "DHT11":
			s = DHT.DHT11
		elif self.conf["sensor"]["type"] == "AM2302":
			s = DHT.AM2302
		else:
			self.log.write.warning('Wrong sensor type, allowed type: "DHT22", "DHT11", "AM2302"')
			self.forceQuit(True)
		
		if isinstance(self.conf["sensor"]["pin"], int) and self.conf["sensor"]["pin"] <= 40:
			h,t = DHT.read_retry(s, self.conf["sensor"]["pin"])
			self.log.write.debug("Sensor: {0}, pin: {1}, reading - temp: {2}*C and hum: {3}%".format(s, self.conf["sensor"]["pin"], t, h))
			if h != None and t != None:
				return (float("{0:0.2f}".format(t)), float("{0:0.2f}".format(h)))
			else:
				self.log.write.warning("Sensor returned None values! Aborting script.")
				self.forceQuit(True)
		else:
			self.log.write.critical("Sensor pin: '{0}' is not integer type!".format(self.conf["sensor"]["pin"]))
			self.forceQuit(True)
			
	def checkBoiler(self):
		if(GPIO.input(self.conf["relay"]) == 1 and self.targetTemp + self.conf["treshold"][1] < self.currentTemp[0]) or (GPIO.input(self.conf["relay"]) == 0 and self.targetTemp + self.conf["treshold"][0]  > self.currentTemp[0]):
			self.log.write.info('Changing relay state from {0} -> {1}'.format(bool(GPIO.input(self.conf["relay"])), not bool(GPIO.input(self.conf["relay"]))))
			GPIO.output(self.conf["relay"], not GPIO.input(self.conf["relay"])) # change relay state
			return True
		else:
			self.log.write.debug('Letting relay be in current state: "{0}"'.format(bool(GPIO.input(self.conf["relay"]))))
			return False		
			
class log:
	'at least it use some logging'
	def __init__(self, logPath = "thermometer.log", size = 1048576, backup = 10, level = "INFO"):
		self.logPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), logPath)
		self.size = size
		self.backup = backup
		self.level = level
		self.logPath = logPath
		
		self.setLogger()
		
	def setLogger(self):
		self.write = logging.getLogger()
		
		#ugly thing, don't look at it, please...
		if self.level == "DEBUG":
			self.write.setLevel(logging.DEBUG)
		if self.level == "INFO":
			self.write.setLevel(logging.INFO)
		# i said don't look at it, you #!?^ˇĐ[đĐ[{]
		if self.level == "WARNING":
			self.write.setLevel(logging.WARNING)
		if self.level == "CRITICAL":
			self.write.setLevel(logging.CRITICAL)
		
		handler = logging.handlers.RotatingFileHandler(self.logPath, maxBytes=self.size, backupCount=self.backup)
		handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
		self.write.addHandler(handler)

class db:
	'This docstring is intentionally left blank'
	def __init__(self, therm, dbPath = "tempDB.sqlite3"):
		self.therm = therm
		self.dbPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), dbPath)
		self.conn = sqlite3.connect(self.dbPath)
		self.cursor = self.conn.cursor()
		self.cursor.execute("CREATE TABLE IF NOT EXISTS log(time DATETIME PRIMARY KEY NOT NULL, temp REAL NOT NULL, hum REAL NOT NULL, relay INTEGER)")
		self.conn.commit()
	
	def insert(self):
		self.cursor.execute("INSERT INTO log (time, temp, hum, relay) VALUES ('{0}','{1}','{2}',{3})".format(datetime.datetime.now().isoformat(' '), self.therm.currentTemp[0], self.therm.currentTemp[1], GPIO.input(self.therm.conf["relay"])))
		self.conn.commit()
		
	def __del__(self):
		self.conn.close()
		
class remoteLog:
	'mel by ses naucit dokumentovat si kod...'
	def __init__(self, therm):
		self.therm = therm
	def upload(self, dict = {}):
		dict['date'] = datetime.datetime.now().isoformat(' ')
		dict['directive'] = json.JSONEncoder().encode(self.therm.directive)
		dict['targetTemp'] = self.therm.targetTemp
		dict['currentTemp'] = self.therm.currentTemp[0]
		dict['currentHum'] = self.therm.currentTemp[1]
		dict['relay'] = GPIO.input(self.therm.conf["relay"])
		url_values = parse.urlencode(dict)
		url = self.therm.conf['server'] + '?' + url_values
		self.therm.log.write.debug("Contacting url: {0}".format(url))
		data = request.urlopen(url)
		data = data.read().decode('utf-8')
		if data == "True":
			self.therm.log.write.debug('Remote server accepted request')
		else:
			self.therm.log.write.info('Remote server DID NOT accepted request, returned: {0}'.format(data))