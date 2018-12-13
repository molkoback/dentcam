from PyQt5.QtWidgets import QApplication

import os

org = "DentCam"
name = "DentCam"
version = "1.2.0"

data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

class App(QApplication):
	def __init__(self, argv):
		super().__init__(argv)
		QApplication.setOrganizationName(org)
		QApplication.setApplicationName(name)
		QApplication.setApplicationVersion(version)
