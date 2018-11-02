from .camera import getCameraDevices

from PyQt5.QtCore import QSettings, pyqtSignal
from PyQt5.QtWidgets import QDialog, QFileDialog, QApplication, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel, QCheckBox, QPushButton, QComboBox

class DCOptionsWin(QDialog):
	
	saveSignal = pyqtSignal()
	loadSignal = pyqtSignal()
	
	def __init__(self, parent):
		super().__init__(parent)
		
		self.outputPath = "."
		self.cfgPath = "."
		
		self.flipHorizCheckBox = QCheckBox()
		self.flipVertCheckBox = QCheckBox()
		
		self.settings = self.createSettings()
		self.createLayout()
		self.loadSettings()
	
	@property
	def flipHoriz(self):
		return self.flipHorizCheckBox.isChecked()
	
	@property
	def flipVert(self):
		return self.flipVertCheckBox.isChecked()
	
	def createSettings(self):
		return QSettings(QApplication.organizationName(), QApplication.applicationName())
	
	def loadSettings(self):
		self.outputPath = self.settings.value("images/save_path", ".")
		self.flipHorizCheckBox.setChecked(bool(self.settings.value("images/flip_horiz", False)))
		self.flipVertCheckBox.setChecked(bool(self.settings.value("images/flip_vert", False)))
		self.cfgPath = self.settings.value("pfs/pfs_path", ".")
		self.loadSignal.emit()
	
	def saveSettings(self):
		self.settings.setValue("images/save_path", self.outputPath)
		self.settings.setValue("images/flip_horiz", int(self.flipHoriz))
		self.settings.setValue("images/flip_vert", int(self.flipVert))
		self.settings.setValue("pfs/pfs_path", self.cfgPath)
		self.settings.sync()
		self.saveSignal.emit()
	
	def createLayout(self):
		vbox = QVBoxLayout()
		
		imagesGroupBox = QGroupBox("Saved Images")
		form = QFormLayout()
		form.addRow(QLabel("Flip Horizontally"), self.flipHorizCheckBox)
		form.addRow(QLabel("Flip Vertically"), self.flipVertCheckBox)
		outputPathButton = QPushButton("Browse...")
		outputPathButton.clicked.connect(self.on_outputPathButtonClicked)
		form.addRow(QLabel("Save Folder"), outputPathButton)
		imagesGroupBox.setLayout(form)
		vbox.addWidget(imagesGroupBox)
		
		filesGroupBox = QGroupBox("Config Files")
		form = QFormLayout()
		cfgPathButton = QPushButton("Browse...")
		cfgPathButton.clicked.connect(self.on_cfgPathButtonClicked)
		form.addRow(QLabel("Config folder"), cfgPathButton)
		filesGroupBox.setLayout(form)
		vbox.addWidget(filesGroupBox)
		
		vbox.addStretch()
		
		hbox = QHBoxLayout()
		okButton = QPushButton("OK")
		hbox.addWidget(okButton)
		okButton.clicked.connect(self.on_okButtonClicked)
		cancelButton = QPushButton("Cancel")
		cancelButton.clicked.connect(self.on_cancelButtonClicked)
		hbox.addWidget(cancelButton)
		vbox.addLayout(hbox)
		
		self.setLayout(vbox)
	
	def on_outputPathButtonClicked(self):
		path = QFileDialog.getExistingDirectory(self, "Open Folder",  self.outputPath)
		if path:
			self.outputPath = path
	
	def on_cfgPathButtonClicked(self):
		path = QFileDialog.getExistingDirectory(self, "Open Folder",  self.cfgPath)
		if path:
			self.cfgPath = path
	
	def on_okButtonClicked(self):
		self.saveSettings()
		self.hide()
	
	def on_cancelButtonClicked(self):
		self.loadSettings()
		self.hide()
