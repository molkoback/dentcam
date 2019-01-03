from .app import data_path

from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication

from pypylon import pylon

import json
import logging
import os

class Converter:
	def __init__(self):
		self.pylonConverter = pylon.ImageFormatConverter()
		self.pylonConverter.OutputPixelFormat = pylon.PixelType_RGB8packed
		self.pylonConverter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
	
	def ndarray2QImage(self, ar):
		image = QImage(ar, ar.shape[1], ar.shape[0], QImage.Format_RGB888)
		return image.copy() # Not using a copy causes a crash
	
	def convert(self, grabResult):
		ar = self.pylonConverter.Convert(grabResult).GetArray()
		return self.ndarray2QImage(ar)

class Camera:
	def __init__(self, device, **kwargs):
		self.device = device
		self.nick = kwargs.get("nick", "")
		
		self.grabParamsFile = kwargs.get(
			"grabParamsFile",
			os.path.join(data_path, "pfs", "grab.pfs")
		)
		self.snapParamsFile = kwargs.get(
			"snapParamsFile",
			os.path.join(data_path, "pfs", "snap.pfs")
		)
		
		self.pylonCamera = None
		self.converter = Converter()
		self.grabbing = False
	
	def __repr__(self):
		return "<Camera: '%s'>" % self.name
	
	@property
	def name(self):
		return self.nick if self.nick else self.device
	
	def open(self):
		tlFactory = pylon.TlFactory.GetInstance()
		pylonDeviceInfos = tlFactory.EnumerateDevices()
		for pdi in pylonDeviceInfos:
			if pdi.GetFriendlyName() == self.device:
				pylonCamera = pylon.InstantCamera()
				pylonCamera.Attach(tlFactory.CreateDevice(pdi))
				self.pylonCamera = pylonCamera
				return True
		return False
	
	def close(self):
		self.pylonCamera.Close()
	
	def loadParams(self, fn):
		pylon.FeaturePersistence.Load(fn, self.pylonCamera.GetNodeMap(), True)
	
	def grabNext(self):
		""" Grabs the next image from camera array. """
		return self.pylonCamera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
	
	def grab(self):
		""" Video mode. Yields QImage. """
		self.pylonCamera.Open()
		self.grabbing = True
		self.loadParams(self.grabParamsFile)
		
		# Use two loops to prevent stops caused by whatever
		while self.grabbing:
			self.pylonCamera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
			while self.grabbing and self.pylonCamera.IsGrabbing():
				grabResult = self.grabNext()
				if grabResult.GrabSucceeded():
					yield self.converter.convert(grabResult)
			self.pylonCamera.StopGrabbing()
		self.pylonCamera.Close()
	
	def stop(self):
		self.grabbing = False
	
	def snap(self):
		self.pylonCamera.Open()
		self.loadParams(self.snapParamsFile)
		self.pylonCamera.StartGrabbing(pylon.GrabStrategy_OneByOne)
		grabResult = self.grabNext()
		self.pylonCamera.StopGrabbing()
		self.pylonCamera.Close()
		return self.converter.convert(grabResult)
	
	def toDict(self):
		return {
			"device": self.device,
			"nick": self.nick,
			"grabParamsFile": self.grabParamsFile,
			"snapParamsFile": self.snapParamsFile
		}
	
	def toJSON(self, fn):
		with open(fn, "w") as fp:
			json.dump(self.toDict())
	
	@classmethod
	def fromDict(cls, d):
		return cls(
			d["device"],
			nick=d["nick"],
			grabParamsFile=d["grabParamsFile"],
			snapParamsFile=d["snapParamsFile"]
		)
	
	@classmethod
	def fromJSON(cls, fn):
		with open(fn) as fp:
			d = json.load(fp)
		return cls.fromDict(d)

class CameraWorker(QObject):
	
	grabStartedSignal = pyqtSignal()
	grabStoppedSignal = pyqtSignal()
	
	sendGrabSignal = pyqtSignal(QImage)
	sendSnapshotSignal = pyqtSignal(QImage)
	
	def __init__(self, cam):
		super().__init__()
		self.cam = cam
		self.grabbing = False
	
	def grabloop(self):
		for image in self.cam.grab():
			self.sendGrabSignal.emit(image)
			QApplication.processEvents()
			if not self.grabbing:
				self.cam.stop()
	
	@pyqtSlot()
	def startGrabSlot(self):
		self.grabbing = True
		self.grabStartedSignal.emit()
		self.grabloop()
		self.grabStoppedSignal.emit()
	
	@pyqtSlot()
	def stopGrabSlot(self):
		self.grabbing = False
	
	@pyqtSlot()
	def snapshotSlot(self):
		self.sendSnapshotSignal.emit(self.cam.snap())

class CameraControl(QObject):
	
	startGrabSignal = pyqtSignal()
	stopGrabSignal = pyqtSignal()
	snapshotSignal = pyqtSignal()
	
	def __init__(self, parent, label, camera):
		super().__init__(parent)
		self.worker = CameraWorker(camera)
		
		self.grabbing = False
		
		self.snapshotResult = None
		self.snapshotReceived = False
		
		self.startGrabSignal.connect(self.worker.startGrabSlot)
		self.stopGrabSignal.connect(self.worker.stopGrabSlot)
		self.snapshotSignal.connect(self.worker.snapshotSlot)
		
		self.worker.grabStartedSignal.connect(self.grabStartedSlot)
		self.worker.grabStoppedSignal.connect(self.grabStoppedSlot)
		self.worker.sendSnapshotSignal.connect(self.receiveSnapshotSlot)
		
		self.worker.sendGrabSignal.connect(label.receiveGrabSlot)
		
		thread = QThread(self)
		self.worker.moveToThread(thread)
		thread.start()
	
	def startGrab(self):
		self.startGrabSignal.emit()
		logging.debug("starting grab")
		while not self.grabbing:
			QApplication.processEvents()
	
	def stopGrab(self):
		self.stopGrabSignal.emit()
		logging.debug("stopping grab")
		while self.grabbing:
			QApplication.processEvents()
	
	def snapshot(self):
		self.stopGrab()
		
		self.snapshotSignal.emit()
		logging.debug("receiving snapshot")
		while not self.snapshotReceived:
			QApplication.processEvents()
		self.snapshotReceived = False
		
		self.startGrab()
		
		return self.snapshotResult
	
	@pyqtSlot()
	def grabStartedSlot(self):
		self.grabbing = True
	
	@pyqtSlot()
	def grabStoppedSlot(self):
		self.grabbing = False
	
	@pyqtSlot(QImage)
	def receiveSnapshotSlot(self, image):
		self.snapshotResult = image
		self.snapshotReceived = True

def getCameraDevices(maxDevices=-1):
	tlFactory = pylon.TlFactory.GetInstance()
	pylonDeviceInfos = tlFactory.EnumerateDevices()
	if maxDevices >= 0:
		pylonDeviceInfos = pylonDeviceInfos[0:maxDevices]
	devices = [pdi.GetFriendlyName() for pdi in pylonDeviceInfos]
	devices.sort()
	return devices

"""
def getCameraDevices(maxDevices=-1):
	tlFactory = pylon.TlFactory.GetInstance()
	pylonDeviceInfos = tlFactory.EnumerateDevices()
	if maxDevices >= 0:
		pylonDeviceInfos = pylonDeviceInfos[0:maxDevices]
	devices = [Device(pdi) for pdi in pylonDeviceInfos]
	devices.sort(key=lambda d: d.name)
	return devices
"""
