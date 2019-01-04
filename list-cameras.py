#!/usr/bin/env python3

from dentcam.camera import getCameraDevices

if __name__ == "__main__":
	devices = getCameraDevices()
	print("Found %d camera devices:" % len(devices))
	print("\n".join(devices))
