# VF Render Lottie

EARLY ALPHA VERSION - Renders polygons as animated shapes to the Lottie JSON format

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
