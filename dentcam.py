#!/usr/bin/env python3

from dentcam.app import App
from dentcam.mainwin import MainWin

import sys
import logging

loglevel = logging.DEBUG

def initLogs():
	root = logging.getLogger()
	root.setLevel(loglevel)
	ch = logging.StreamHandler(sys.stdout)
	ch.setLevel(loglevel)
	formatter = logging.Formatter(
		"[%(asctime)s][%(levelname)s] %(module)s.py:%(lineno)d: %(message)s",
		datefmt="%H:%M:%S"
	)
	ch.setFormatter(formatter)
	root.addHandler(ch)

if __name__ == "__main__":
	initLogs()
	app = App(sys.argv)
	win = MainWin()
	sys.exit(app.exec_())
