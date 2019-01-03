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
		
		self.cameras = []
		self.cameraComboBox = QComboBox()
		self.loadCameras()
		
		self.folderLineEdit = QLineEdit()
		
		self.switching = False
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
		
		hbox.addWidget(QLabel("Camera:"))
		self.cameraComboBox.currentIndexChanged.connect(self.cameraChangedSlot)
		hbox.addWidget(self.cameraComboBox)
		
		hbox.addStretch()
		hbox.addWidget(QLabel("Folder:"))
		hbox.addWidget(self.folderLineEdit)
		self.folderLineEdit.returnPressed.connect(lambda: self.folderLineEdit.clearFocus())
		
		vbox.addLayout(hbox)
		
		self.setCamera(None)
		vbox.addWidget(self.camLabel)
		self.imgLabel.setImage(QImage(os.path.join(data_path, "img", "images.png")))
		vbox.addWidget(self.imgLabel)
		
		self.setCentralWidget(w)
		self.restoreGeometry(self.options.geometry)
	
	def loadCameras(self):
		path = os.path.join(self.options.cfgPath, "*.json")
		cameras = [Camera.fromJSON(fn) for fn in glob.glob(path)]
		cameras.sort(key=lambda cam: cam.name)
		self.cameras = [None] + cameras
		
		# Update QComboBox
		items = ["None"] + [cam.name for cam in cameras]
		self.cameraComboBox.clear()
		self.cameraComboBox.addItems(items)
		
		# Add shortcuts for cameras
		for i in range(len(self.cameras)):
			f = functools.partial(self.cameraComboBox.setCurrentIndex, i)
			self.addAction(Action(self, "", f, "Ctrl+%d" % i))
	
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
		path = os.path.join(
			self.options.outputPath,
			self.folderLineEdit.text().strip()
		)
		if not os.path.exists(path):
			os.mkdir(path)
		fn = os.path.join(path, "%d.jpg" % int(time.time()*1000))
		return fn
	
	def saveImage(self, path):
		image = self.imgLabel.image()
		if not image:
			return
		logging.debug("saving '%s'" % path)
		image = image.mirrored(
			horizontal=self.options.flipHoriz,
			vertical=self.options.flipVert
		)
		if not image.save(path, quality=100):
			QMessageBox.critical(self, "Couldn't Save Image", "Couldn't Save Image '%s'." % path)
	
	def on_saveAction(self):
		path = self.savePath()
		self.saveImage(path)
	
	def on_saveAsAction(self):
		path = QFileDialog.getSaveFileName(
			self,
			"Save Image",
			self.options.outputPath, "Image File (*.png *.jpg *.bmp)"
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
	
	def setCamera(self, cam):
		if self.switching:
			return False
		self.switching = True
		self.snapAction.setEnabled(False)
		
		# Stop the current camera
		if self.camControl:
			self.camControl.stopGrab()
			self.camControl = None
		
		# Show blank image if we don't have camera
		if cam == None:
			self.camLabel.setImage(QImage(os.path.join(data_path, "img", "camera.png")))
			self.switching = False
			return True
		
		# Try to open camera
		try:
			if not cam.open():
				raise Exception()
			self.camControl = CameraControl(self, self.camLabel, cam)
			self.camControl.startGrab()
		except:
			QMessageBox.critical(self, "Couldn't Open Camera", "Couldn't Open Camera '%s'." % cam.name)
			self.camControl = None
			return self.setCamera(None)
		
		# Camera opened successfully
		self.snapAction.setEnabled(True)
		self.switching = False
		return True
	
	@pyqtSlot(int)
	def cameraChangedSlot(self, index):
		if index >= 0:
			self.setCamera(self.cameras[index])
	
	@pyqtSlot()
	def saveOptionsSlot(self):
		self.loadCameras()
	
	def closeEvent(self, e):
		self.options.geometry = self.saveGeometry()
		self.options.save()
