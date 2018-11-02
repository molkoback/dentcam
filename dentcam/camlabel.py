from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel

class CamLabel(QLabel):
	def __init__(self, parent):
		super().__init__(parent)
		self._image = None
		self.setMinimumWidth(480)
		self.setMinimumHeight(360)
	
	def image(self):
		return self._image
	
	def setImage(self, image):
		self._image = image
		pixmap = QPixmap.fromImage(self._image).scaled(
			self.width(), self.height(),
			Qt.KeepAspectRatio,
			Qt.SmoothTransformation
		)
		self.setPixmap(pixmap)
	
	@pyqtSlot(QImage)
	def receiveGrabSlot(self, image):
		self.setImage(image)
