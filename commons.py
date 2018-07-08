#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import stat
import sys

def checkRights():
	global _running
	if os.getuid() != 0:
		return False
	else:
		return True


def chmod():
	st = os.stat('snipsRestart.sh')
	os.chmod('snipsRestart.sh', st.st_mode | stat.S_IEXEC)


def backupConfs(logger):
	if '--remove-backup' in sys.argv and os.path.isfile('backup.txt'):
		logger.info('Backup flagged for deletion, deleting...')
		os.remove('backup.txt')

	if not os.path.isfile('backup.txt'):
		logger.info('Creating configuration backup')
		with open('backup.txt', 'w') as f:
			for line in open('/etc/snips.toml'):
				f.write(line)

		logger.info('Backup made')
	else:
		logger.info('Backup already available')
