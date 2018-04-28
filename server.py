#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
import os
import paho.mqtt.client as mqtt
import pytoml
import socket
import stat
import subprocess
import time

logging.basicConfig(
	format='%(asctime)s [%(threadName)s] - [%(levelname)s] - %(message)s',
	level=logging.INFO,
	filename='serverlogs.log',
	filemode='w'
)

_logger = logging.getLogger('SatConnectServer')
_logger.addHandler(logging.StreamHandler())

_mqttClient = None
_snipsConf = None


def checkRights():
	global _running
	if os.getuid() != 0:
		_logger.error('Please start this tool with sudo')
		_running = False


def chmod():
	st = os.stat('snipsRestart.sh')
	os.chmod('snipsRestart.sh', st.st_mode | stat.S_IEXEC)


def getIp():
	global MY_IP
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.connect(("8.8.8.8", 80))
	MY_IP = s.getsockname()[0]
	s.close()
	_logger.info('Server ip: {}'.format(MY_IP))


def checkAndLoadSnipsConfigurations():
	global _snipsConf, _running

	if os.path.isfile('/etc/snips.toml'):
		backupConfs()
		with open('/etc/snips.toml') as confFile:
			_snipsConf = pytoml.load(confFile)
		_logger.info('Configurations loaded')
	else:
		_logger.error('Snips configuration file not found! Make sure to install Snips prior to use this tool')
		_running = False
	connectMqtt()


def backupConfs():
	if not os.path.isfile('backup.txt'):
		_logger.info('Creating configuration backup')
		with open('backup.txt', 'w') as f:
			for line in open('/etc/snips.toml'):
				f.write(line)

		_logger.info('Backup made')
	else:
		_logger.info('Backup already available')


def connectMqtt():
	global _mqttClient, _coreIp, _running

	try:
		if _mqttClient is not None:
			_mqttClient.loop_stop()
			_mqttClient.disconnect()

		_mqttClient = mqtt.Client()
		_mqttClient.connect('localhost', 1883)
		_mqttClient.on_message = onMessage
		_mqttClient.subscribe('satConnect/server/checkAvailability')
		_mqttClient.subscribe('satConnect/server/addSatellite')
		_mqttClient.loop_start()
	except socket.error:
		_logger.error("Couldn't connect to mqtt localhost server, aborting")
		_running = False


def checkNameAvailability(name):
	global _snipsConf

	_logger.warning('Checking name availability for satellite "{}"'.format(name))
	name = '{}@mqtt'.format(name)
	if 'audio' not in _snipsConf['snips-hotword'] or name not in _snipsConf['snips-hotword']['audio']:
		_logger.info('Satellite name "{}" is free'.format(name))
		return True

	_logger.warning('Satellite name "{}" is already declared'.format(name))
	return False


def addSatellite(name):
	global _snipsConf

	_logger.info('Adding satellite')

	try:
		if 'bind' not in _snipsConf['snips-audio-server']:
			_snipsConf['snips-audio-server']['bind'] = 'default@mqtt'

		if 'audio' not in _snipsConf['snips-hotword']:
			_snipsConf['snips-hotword']['audio'] = ['default@mqtt']

		name = '{}@mqtt'.format(name)

		if name not in _snipsConf['snips-hotword']['audio']:
			_snipsConf['snips-hotword']['audio'].append(name)

		f = open('/etc/snips.toml', 'w')
		pytoml.dump(_snipsConf, f)
		f.close()

		restartSnips()
	except:
		_logger.error('Updating and restarting Snips failed')
		_mqttClient.publish('satConnect/server/confUpdateFailed', json.dumps({}))


def restartSnips():
	global _running
	_logger.info('Restarting local Snips')
	subprocess.call(['./snipsRestart.sh'])
	_mqttClient.publish('satConnect/server/confUpdated', json.dumps({}))
	_logger.info('All done!')
	_running = False


def onMessage(client, userData, message):
	payload = json.loads(message.payload)

	if message.topic == 'satConnect/server/checkAvailability':
		if not checkNameAvailability(payload['name']):
			_mqttClient.publish('satConnect/satellites/notAvailable', json.dumps({}))
		else:
			_mqttClient.publish('satConnect/satellites/available', json.dumps({}))

	elif message.topic == 'satConnect/server/addSatellite':
		addSatellite(payload['name'])


_running = False
if __name__ == '__main__':
	_logger.info('Starting up Snips SatConnect Server')
	_running = True
	try:
		checkRights()
		chmod()
		getIp()
		checkAndLoadSnipsConfigurations()
		while _running:
			time.sleep(0.1)
	except KeyboardInterrupt:
		_running = False
		pass
	finally:
		_logger.info('\nShutting down Snips SatConnect Server')
		if _mqttClient is not None:
			_mqttClient.loop_stop()
			_mqttClient.disconnect()