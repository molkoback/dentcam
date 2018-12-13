from .app import data_path
from .optionswin import OptionsWin
from .camera import Camera, CameraControl, getCameraDevices
from .camlabel import CamLabel

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QImage, QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, QVBoxLayout, QHBoxLayout, QMessageBox, QFileDialog, QLabel, QPushButton, QComboBox, QLineEdit

import functools
import logging
import os
import glob
import sys
import time

_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

class Action(QAction):
	def __init__(self, parent, text, action, shortcut=None, enabled=True):
		super().__init__(text, parent)
		if shortcut:
			self.setShortcut(shortcut)
		self.triggered.connect(action)
		self.setEnabled(enabled)

class MainWin(QMainWindow):
	def __init__(self):
		super().__init__()
		
		self.options = OptionsWin(self)
		self.options.saveSignal.connect(self.saveOptionsSlot)
		
		self.devices = []
		self.deviceComboBox = QComboBox()
		self.cfgFiles = []
		self.cfgComboBox = QComboBox()
		self.deviceCfg = {}
		
		self.folderLineEdit = QLineEdit()
		
		self.camControl = None
		self.camLabel = CamLabel(self)
		self.imgLabel = CamLabel(self)
		
		self.createWindow()
		self.createMenu()
		self.createLayout()
	
	def createWindow(self):
		self.setWindowIcon(QIcon(os.path.join(data_path, "img", "icon.png")))
		self.show()
	
	def createMenu(self):
		self.mainMenu = self.menuBar()
		
		fileMenu = self.mainMenu.addMenu("File")
		self.snapAction = Action(self, "Snap", self.on_snapAction, "Space", False)
		fileMenu.addAction(self.snapAction)
		self.saveAction = Action(self, "Save", self.on_saveAction, "Ctrl+S", False)
		fileMenu.addAction(self.saveAction)
		self.saveAsAction = Action(self, "Save As...", self.on_saveAsAction, "Ctrl+Shift+S", False)
		fileMenu.addAction(self.saveAsAction)
		fileMenu.addAction(Action(self, "Quit", lambda: self.close(), "Ctrl+Q"))
		
		toolsMenu = self.mainMenu.addMenu("Tools")
		toolsMenu.addAction(Action(self, "Options", self.options.show))
		
		helpMenu = self.mainMenu.addMenu("Help")
		helpMenu.addAction(Action(self, "About", self.on_aboutAction))
		helpMenu.addAction(Action(self, "About Qt", lambda: QMessageBox.aboutQt(self)))
	
	def createLayout(self):
		w = QWidget()
		vbox = QVBoxLayout()
		w.setLayout(vbox)
		
		hbox = QHBoxLayout()
		
		self.updateDevices()
		hbox.addWidget(QLabel("Device:"))
		self.deviceComboBox.currentIndexChanged.connect(self.deviceChangedSlot)
		hbox.addWidget(self.deviceComboBox)
		
		self.updateCfgFiles()
		hbox.addWidget(QLabel("Config File:"))
		self.cfgComboBox.currentIndexChanged.connect(self.cfgChangedSlot)
		hbox.addWidget(self.cfgComboBox)
		
		hbox.addStretch()
		hbox.addWidget(QLabel("Folder:"))
		hbox.addWidget(self.folderLineEdit)
		self.folderLineEdit.returnPressed.connect(lambda: self.folderLineEdit.clearFocus())
		
		vbox.addLayout(hbox)
		
		self.setCamera(self.devices[0], self.cfgFiles[0])
		vbox.addWidget(self.camLabel)
		self.imgLabel.setImage(QImage(os.path.join(data_path, "img", "images.png")))
		vbox.addWidget(self.imgLabel)
		
		self.setCentralWidget(w)
		self.restoreGeometry(self.options.geometry)
	
	def updateDevices(self):
		self.devices = [None] + getCameraDevices()
		
		# Update QComboBox
		items = ["None"] + [device.name for device in self.devices[1:]]
		self.deviceComboBox.clear()
		self.deviceComboBox.addItems(items)
		
		# Add shortcuts for cameras
		for i in range(len(self.devices)):
			f = functools.partial( self.deviceComboBox.setCurrentIndex, i)
			self.addAction(Action(self, "", f, "Ctrl+%d" % i))
	
	def updateCfgFiles(self):
		path = os.path.join(self.options.cfgPath, "*.pfs")
		self.cfgFiles = [None] + glob.glob(path)
		
		# Update QComboBox
		self.cfgComboBox.clear()
		items = ["Default"] + [os.path.split(f)[1] for f in self.cfgFiles[1:]]
		self.cfgComboBox.addItems(items)
		
		# Reset device specific config
		self.deviceCfg = {}
	
	def close(self):
		if self.camControl:
			self.camControl.stopGrab()
		super().close()
	
	def on_snapAction(self):
		self.snapAction.setEnabled(False)
		image = self.camControl.snapshot()
		self.imgLabel.setImage(image)
		self.snapAction.setEnabled(True)
		
		# Enable image saving
		self.saveAction.setEnabled(True)
		self.saveAsAction.setEnabled(True)
		
		if self.options.autoSave:
			self.on_saveAction()
	
	def savePath(self):
		path = os.path.join(self.options.outputPath, self.folderLineEdit.text())
		if not os.path.exists(path):
			os.mkdir(path)
		fn = os.path.join(path, "%d.jpg" % int(time.time()*1000))
		return fn
	
	def saveImage(self, path):
		image = self.imgLabel.image()
		if image:
			logging.debug("saving '%s'" % path)
			image = image.mirrored(
				horizontal=self.options.flipHoriz,
				vertical=self.options.flipVert
			)
			image.save(path)
	
	def on_saveAction(self):
		path = self.savePath()
		self.saveImage(path)
	
	def on_saveAsAction(self):
		path = QFileDialog.getSaveFileName(
			self,
			"Save Image",
			self.snapshotPath(), "Image File (*.png *.jpg *.bmp)"
		)
		if path[0]:
			self.saveImage(path[0])
	
	def on_aboutAction(self):
		msg = (
			"{} v{}<br>"
			"<br>"
			"Copyright (C) 2018 <a href=\"mailto:eero.molkoselka@gmail.com\">Eero Molkoselkä</a><br>"
			"<br>"
			"This software is licensed under WTFPL. See COPYING file for details.<br>"
		)
		QMessageBox.about(
			self,
			"About %s" % QApplication.applicationName(),
			msg.format(QApplication.applicationName(), QApplication.applicationVersion())
		)
	
	def setCamera(self, device, cfg):
		# Stop the current camera
		if self.camControl:
			self.camControl.stopGrab()
			self.camControl = None
		
		# Show blank image if we don't have camera
		if device == None:
			self.camLabel.setImage(QImage(os.path.join(data_path, "img", "camera.png")))
			self.snapAction.setEnabled(False)
			return True
		
		# Try to open camera
		try:
			kwargs = {"snapParamsFile": cfg} if cfg else {}
			cam = Camera(device, **kwargs)
			self.camControl = CameraControl(self, self.camLabel, cam)
			self.camControl.startGrab()
		except:
			QMessageBox.critical(self, "Couldn't Open Camera", "Couldn't Open Camera '%s'." % device.name)
			self.camControl = None
			self.setCamera(None, cfg)
			return False
		
		# Enable snapping
		self.snapAction.setEnabled(True)
		return True
	
	@pyqtSlot(int)
	def deviceChangedSlot(self, index):
		di = self.deviceComboBox.currentIndex()
		cfgi = self.cfgComboBox.currentIndex()
		if di < 0 or cfgi < 0:
			return
		
		if di in self.deviceCfg:
			cfgi = self.deviceCfg[di]
		self.cfgComboBox.setCurrentIndex(cfgi)
		self.setCamera(self.devices[di], self.cfgFiles[cfgi])
	
	@pyqtSlot(int)
	def cfgChangedSlot(self, index):
		di = self.deviceComboBox.currentIndex()
		cfgi = self.cfgComboBox.currentIndex()
		if di < 0 or cfgi < 0:
			return
		
		self.deviceCfg[di] = cfgi
		self.setCamera(self.devices[di], self.cfgFiles[cfgi])
	
	@pyqtSlot()
	def saveOptionsSlot(self):
		self.updateCfgFiles()
	
	def closeEvent(self, e):
		self.options.geometry = self.saveGeometry()
		self.options.save()
