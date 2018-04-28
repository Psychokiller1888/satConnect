#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
import os
import paho.mqtt.client as mqtt
import pixels
import pytoml
#import RPi.GPIO as gpio
import socket
import stat
import subprocess
import time

logging.basicConfig(
	format='%(asctime)s [%(threadName)s] - [%(levelname)s] - %(message)s',
	level=logging.INFO,
	filename='satlogs.log',
	filemode='w'
)

_logger = logging.getLogger('SatConnect')
_logger.addHandler(logging.StreamHandler())

_mqttClient = None
_leds = None
_snipsConf = None
_satelliteName = ''
_coreIp = ''


def checkRights():
	global _running
	if os.getuid() != 0:
		_logger.error('Please start this tool with sudo')
		_running = False


def chmod():
	st = os.stat('snipsRestart.sh')
	os.chmod('snipsRestart.sh', st.st_mode | stat.S_IEXEC)


def checkAndLoadSnipsConfigurations():
	global _snipsConf, _running

	if os.path.isfile('/etc/snips.toml'):
		with open('/etc/snips.toml') as confFile:
			_snipsConf = pytoml.load(confFile)
			if 'snips-common' not in _snipsConf:
				_logger.warning('Missing configuration "snips-common" in snips configuration file')
				_snipsConf['snips-common'] = []
			if 'snips-audio-server' not in _snipsConf:
				_logger.warning('Missing configuration "snips-audio-server" in snips configuration file')
				_snipsConf['snips-audio-server'] = []
			if 'mqtt' not in _snipsConf['snips-common']:
				_logger.warning('Missing configuration "snips-common/mqtt" in snips configuration file')
				_snipsConf['snips-common']['mqtt'] = ''
			if 'bind' not in _snipsConf['snips-audio-server']:
				_logger.warning('Missing configuration "snips-audio-server/bind" in snips configuration file')
				_snipsConf['snips-audio-server']['bind'] = ''
	else:
		_logger.error('Snips configuration file not found! Make sure to install Snips prior to use this tool')
		_running = False
	getCoreIp()


def getCoreIp():
	global _coreIp

	while not _coreIp:
		_coreIp = raw_input('Please enter the core ip address (you can get it by starting "server.py" on the main device): ')
		if not _coreIp:
			_logger.warning('Core ip cannot be empty')
			continue

		_logger.info('Checking ip address {}'.format(_coreIp))
		if subprocess.call(['ping', '-q', '-c', '3', _coreIp]) != 0:
			_logger.warning('Ip address {} is not alive on your current network'.format(_coreIp))
			_coreIp = ''
		else:
			_logger.info('Ip address is alive')

	connectMqtt()

def connectMqtt():
	global _mqttClient, _coreIp

	try:
		if _mqttClient is not None:
			_mqttClient.loop_stop()
			_mqttClient.disconnect()

		_mqttClient = mqtt.Client()
		_mqttClient.connect(_coreIp, 1883)
		_mqttClient.on_message = onMessage
		_mqttClient.subscribe('satConnect/satellites/notAvailable')
		_mqttClient.subscribe('satConnect/satellites/available')
		_mqttClient.subscribe('satConnect/server/confUpdated')
		_mqttClient.subscribe('satConnect/server/confUpdateFailed')
		_mqttClient.loop_start()
	except socket.error:
		_logger.error("Couldn't connect to mqtt server on core ip {}".format(_coreIp))
		_coreIp = ''
		getCoreIp()

	defineSatelliteName()


def defineSatelliteName():
	global _satelliteName
	while not _satelliteName:
		_satelliteName = raw_input('Please name this satellite: ')
		if not _satelliteName:
			_logger.warning('Satellite name cannot be empty')
			continue

	checkNameAvailability()


def checkNameAvailability():
	_logger.info('Checking satellite name ({}) availability'.format(_satelliteName))
	_mqttClient.publish('satConnect/server/checkAvailability', json.dumps({'name': _satelliteName}))


def updateTomlConfig():
	global _snipsConf, _coreIp, _satelliteName

	_logger.info('Writting local toml configuration...')
	_snipsConf['snips-common']['mqtt'] = '{}:1883'.format(_coreIp)
	_snipsConf['snips-audio-server']['bind'] = '{}@mqtt'.format(_satelliteName)

	f = open('/etc/snips.toml', 'w')
	pytoml.dump(_snipsConf, f)
	f.close()
	updateCoreToml()


def updateCoreToml():
	global _satelliteName
	_logger.info('Sending core configuration...')
	_mqttClient.publish('satConnect/server/addSatellite', json.dumps({'name': _satelliteName}))


def restartSnips():
	_logger.info('Restarting local Snips')
	subprocess.call(['./snipsRestart.sh'])
	done()


def done():
	global _running
	_logger.info('All done! This satellite is now connected and should respond.')
	raw_input('Press enter')
	_running = False


def onMessage(client, userData, message):
	global _snipsConf, _satelliteName, _running

	if message.topic == 'satConnect/satellites/notAvailable':
		_logger.warning('The satellite name you chose is already taken.')
		_logger.warning('Are you replacing an existing device? If not, continuing may result in collisions!')

		answer = ''
		while not answer:
			try:
				answer = raw_input('I am replacing an old device (Y) / No, change the satellite name (N): ')
				if answer.lower() == 'y':
					updateTomlConfig()
					break
				elif answer.lower() == 'n':
					_satelliteName = ''
					defineSatelliteName()
				else:
					raise ValueError
			except ValueError:
				_logger.warning('Please use Y or N')
				answer = ''
	elif message.topic == 'satConnect/satellites/available':
		_logger.info('The satellite name is available, proceeding with configuration')
		updateTomlConfig()
	elif message.topic == 'satConnect/server/confUpdated':
		_logger.info('Main device updated and restarted')
		restartSnips()
	elif message.topic == 'satConnect/server/confUpdateFailed':
		_logger.error('Unfortunately we were unable to update the main device, aborting')
		_running = False



_running = False
if __name__ == '__main__':
	_logger.info('Starting up Snips SatConnect')
	_leds = pixels.getInstance()
	_leds.off()
	_running = True
	try:
		checkRights()
		chmod()
		checkAndLoadSnipsConfigurations()
		while _running:
			time.sleep(0.1)
	except KeyboardInterrupt:
		_running = False
		pass
	finally:
		_logger.info('\nShutting down Snips SatConnect')
		if _mqttClient is not None:
			_mqttClient.loop_stop()
			_mqttClient.disconnect()
		_leds.off()
		#gpio.cleanup()