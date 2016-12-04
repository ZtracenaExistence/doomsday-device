#!/usr/bin/python3

import datetime, time, json
import RPi.GPIO as GPIO
import Adafruit_DHT as DHT
from statistics import mean

####################
# static variables #
####################

path_to_config = "conf.json"
treshold = (0.5,0.5)

#############
# functions #
#############

def load_config( path ):
	'''
	load_config( path ):
	just litle function to read config JSON as string and return it to parse
	'''
	with open(path) as f:
		read_data = f.read()
	return read_data

def desTemp( dict ):
	'''
	function desTemp( dict ):
	is used to found preset temp for actual time, expect dictionary in format {%time%:temp,...}, return tuple in same format
	'''
	hours = sorted(list(dict.keys()))
	now = datetime.datetime.now().time().strftime("%H:%M")

	needle = [ h for h in hours if h < now ]
	if not needle:
		needle.append(hours[-1])

	return (needle[-1], dict[needle[-1]])

def tempR(s,p,i):
	'''
	function tempR():
	read temp from DHT and return tuple (%temp%,%humidity%), in case of bad reading return False

	'''
	if s == "DHT22":
		s = DHT.DHT22
	elif s == "DHT11":
		s = DHT.DHT11
	elif s == "AM2302":
		s = DHT.AM2302
	else:
		return False

	tL, hL = [], []
	for read in range(0,i):
		h, t = DHT.read_retry(s, p)
		if h is not None and t is not None:
			tL.append(t)
			hL.append(h)
		else:
			return False
		time.sleep(3)
	return ( float("{0:0.2f}".format(mean(tL))), float("{0:0.2f}".format(mean(hL))) )

def changeRelay( pin ):
	'''
	changeRelay( pin ):
	function used to change current state of relay.
	'''
	GPIO.output(pin, not GPIO.input(pin))

def setGPIO( confJSON ):
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)
	GPIO.setup(confJSON["relay"], GPIO.OUT)

def findDHT( confJSON ):
	'''
	this function is used for find default sensor in conf.json (default = master set to true), if this condition is not met, it return dict with first sensor
	'''
	needle = [ h for h in confJSON['sensors'] if h["master"] == True ]
	if not needle:
		needle.append(confJSON['sensors'][0])
	return needle[0]

#########################
# standart program flow #
#########################

config = json.loads(load_config(path_to_config))

if config["manual"]["active"] is not True:
	if datetime.datetime.today().weekday() < 5:
		temp = desTemp(config["week"])
	else:
		temp = desTemp(config["weekend"])
else:
	temp = ("manual",config["manual"]["temp"])

print(temp)

activeDHT = findDHT(config)

reading = tempR(activeDHT["type"],activeDHT["pin"],3)
if reading is False:
	print("func returned false!")
	exit()

print(reading)

setGPIO(config)

#print(GPIO.input(config["relay"]))

#if (nactiPinRele == pravda & pozadovanaTeplota+treshold[1] < reading[0]) nebo (nactiPinRele == nepravda & pozadovanaTeplota-treshold[0] > reading[0]) -> pokud jsou podminky pravda pak zmen stav rele z pravda <-> nepravda

if (GPIO.input(config["relay"]) == 1 and temp[1]+0.5 < reading[0]) or (GPIO.input(config["relay"]) == 0 and temp[1]-0.5 > reading[0]):
	changeRelay(config["relay"])


