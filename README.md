# VF Render Lottie

EARLY ALPHA VERSION - Renders polygons as animated shapes to the Lottie JSON format.

This is intended for a very specific and limited workflow. Please refer to the [Python-Lottie Blender plugin on GitLab](https://mattbas.gitlab.io/python-lottie/downloads.html) for more general purpose use cases.

## Installation

- Requires the Lottie library for Python to be installed inside Blender

	```python
	import subprocess
	import sys
	subprocess.call([sys.executable, "-m", "ensurepip", "--user"])
	subprocess.call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
	subprocess.call([sys.executable,"-m", "pip", "install", "--user", "lottie"])
	```

- Requires element attributes set in Geometry Nodes

	- `Color` attribute set to `Face` with name `Lottie_Fill_Color`

- Current testing is at the one polygon stage; trying this on an actual mesh will likely crash everything

## Features

- Takes current active mesh object and for each polygon creates a new shape, sampling positions for every frame in the Blender timeline, and outputting everything as a .json file using the Lottie Python library
- Supports render variables from [VF Autosave Render + Output Variables](https://github.com/jeinselen/VF-BlenderAutosaveRender)
- Supports custom path input for future integration with [VF Delivery](https://github.com/jeinselen/VF-BlenderDelivery)
- Converts Blender linear colour values to sRGB values during export
