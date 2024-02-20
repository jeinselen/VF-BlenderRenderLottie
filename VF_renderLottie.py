bl_info = {
	"name": "VF Render Lottie",
	"author": "John Einselen",
	"version": (0, 7, 0),
	"blender": (3, 6, 0),
	"location": "Render > Render Lottie",
	"description": "Renders polygons as animated shapes in Lottie JSON format",
	"doc_url": "https://github.com/jeinselen/VF-BlenderRenderLottie",
	"tracker_url": "https://github.com/jeinselen/VF-BlenderRenderLottie/issues",
	"category": "Render"}

# General requirements
import bpy
import bpy_extras
#import mathutils

# Lottie requirements
from lottie import objects
from lottie import Point, Color
from lottie.exporters.core import export_lottie

# VF Autosave Render + Output Variables compatibility requirements
from VF_autosaveRender import replaceVariables
import os

# Dependency installation
#import subprocess
#import sys
#subprocess.call([sys.executable, "-m", "ensurepip", "--user"])
#subprocess.call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
#subprocess.call([sys.executable,"-m", "pip", "install", "--user", "lottie"])

# Check dependency snippet
#try:
#	import lottie
#	print("module 'lottie' is installed")
#except ModuleNotFoundError:
#	print("module 'lottie' is not installed")



###########################################################################
# Render Proxy Animation primary functionality classes

class VF_renderLottie(bpy.types.Operator):
	bl_idname = "render.vf_render_lottie"
	bl_label = "Render Lottie JSON"
	bl_description = "Renders polygons as animated shapes in Lottie JSON format"
	
	filepath: bpy.props.StringProperty()
	
	def execute(self, context):
		# Variables
		scene = bpy.context.scene
		width = scene.render.resolution_x
		height = scene.render.resolution_y
		start = scene.frame_start
		end = scene.frame_end
		frame_original = scene.frame_current
		position_precision = 1
#		position_frames = 5
		color_precision = 4
#		color_frames = 10
		fill_color_string = "Lottie_Fill_Color"
		stroke_color_string = "Lottie_Stroke_Color"
		stroke_width_string = "Lottie_Stroke_Width"
		
		# Get active camera
		cam = scene.camera
		
		# Get depsgraph
		deps = bpy.context.evaluated_depsgraph_get()
		
		# Get active object
		obj = bpy.context.active_object
		
		# Get file path
		if self.filepath:
#			print("self.filepath: ", self.filepath)
			filepath = self.filepath
		else:
			filepath = scene.render.filepath
		
		# Support VF Autosave Render + Output Variables if plugin is installed and enabled
		if bpy.context.preferences.addons['VF_autosaveRender']:
			# Filter output file path if enabled
			if bpy.context.preferences.addons['VF_autosaveRender'].preferences.render_output_variables:
				# Check if the serial variable is used
				if '{serial}' in filepath:
					filepath = filepath.replace("{serial}", format(bpy.context.scene.autosave_render_settings.output_file_serial, '04'))
					bpy.context.scene.autosave_render_settings.output_file_serial += 1
				
				# Replace scene filepath output with the processed version
				filepath = replaceVariables(filepath)
		
		# Convert relative path into absolute path for Python compatibility
		filepath = bpy.path.abspath(filepath)
		
		# Create the directory structure if it doesn't already exist
		directorypath = os.path.dirname(filepath)
		if not os.path.exists(directorypath):
			os.makedirs(directorypath)
		
		# Add file format
		filepath += ".json"
		
		# Initialize Lottie animation
		an = objects.Animation(59)
		an.width = width
		an.height = height
		an.in_point = start
		an.out_point = end
		an.frame_rate = scene.render.fps
		# Define metadata
		an.author = "John Einselen"
		an.generator = "VF Blender Lottie Polys"
		
		# Create layer
		layer = an.add_layer(objects.ShapeLayer())
#		layer.name = obj.name
#		layer.width = width
#		layer.height = height
#		layer.size = Point(width, height)
		
		# Track elements that will created for each polygon
		paths_dict = {}
		fills_dict = {}
		
		# Track history of elements (keyframes are added only if changes are detected)
		bez_hist = []
		bez_frame = []
		rgb_hist = []
		rgb_frame = []
		
		# TODO implement linear versus hold keyframes, so changes after multiple frames without changes are detected and set to hold
		# Hold is preferable to linear over two frames due to high frame rate interpolation (similar to issues in Unity)
		
		# Process timeline
		for i in range(end - start):
			frame = start + i
			scene.frame_set(frame)
			
			# Get evaluated object
			obj = obj.evaluated_get(deps)
			mesh = obj.data
			
			# Loop through polygons
			for polygon in mesh.polygons:
				pi = polygon.index
				
				# Get path data as Bezier path
				bez = objects.Bezier()
				bez.close()
				bez_arr = []
				for i in polygon.vertices:
					# Get world position (3D)
					wpos = obj.matrix_world @ mesh.vertices[i].co
					# Get render position (2D)
					rpos = bpy_extras.object_utils.world_to_camera_view(scene, cam, wpos)
					# Reduce precision and flip Y
					xy = [round(rpos.x * width, position_precision), round((1.0 - rpos.y) * height, position_precision)]
					# Add point to path (Y is flipped)
					bez.add_point(Point(xy[0], xy[1]))
					# Add to array
					bez_arr.append(xy)
				
				# Get fill data as Color object
				rgb = linear2srgb(mesh.attributes[fill_color_string].data[pi].color)
				# Replace with reduced precision array
				rgb = [round(rgb[0], color_precision), round(rgb[1], color_precision), round(rgb[2], color_precision)]
				# Add to array
				rgb_arr = []
				rgb_arr.append(rgb[0])
				rgb_arr.append(rgb[1])
				rgb_arr.append(rgb[2])
				
				# First frame
				if (frame == start):
					# Create polygon group
					group = layer.add_shape(objects.Group())
					
					# Create path
					path = group.add_shape(objects.Path())
					path.shape.value = bez
					
					# Get color data and create fill
					fill = group.add_shape(objects.Fill(Color(rgb[0], rgb[1], rgb[2])))
					
					# Store references to path and fill in dictionaries
					paths_dict[pi] = path
					fills_dict[pi] = fill
					
					bez_hist.append(bez_arr)
					rgb_hist.append(rgb_arr)
				
				# Subsequent frames
				else:
					# Reference previously created path and fill from dictionaries
					path = paths_dict[pi]
					fill = fills_dict[pi]
					
					# Add keyframes
					if (bez_hist[pi] != bez_arr):
#						print("")
#						print("history: ", bez_hist[pi][0])
#						print("new:     ", bez_arr[0])
#						print("")
						path.shape.add_keyframe(frame, bez)
					if (rgb_hist[pi] != rgb_arr):
#						print("")
#						print("history: ", rgb_hist[pi])
#						print("new:     ", rgb_arr)
#						print("")
						fill.color.add_keyframe(frame, Color(rgb[0], rgb[1], rgb[2]))
				
				# Store history references
				bez_hist[pi] = bez_arr
				rgb_hist[pi] = rgb_arr
				
				# Remove temp variables
				del bez, bez_arr, rgb, rgb_arr
		
		# Export Lottie JSON file
		export_lottie(an, filepath)
		
		# Reset timeline to original frame number
#		scene.frame_set(frame_original)
		
		return {'FINISHED'}



###########################################################################
# Linear and sRGB conversion functions

# References:
# https://blenderartists.org/t/help-please-is-there-a-fast-way-to-convert-srgb-values-to-linear/631849/25
# http://www.cyril-richon.com/blog/2019/1/23/python-srgb-to-linear-linear-to-srgb
# https://entropymine.com/imageworsener/srgbformula/

def s2l(s):
	if s <= 0.0:
		return 0.0
#	elif s <= 0.0404482362771082: # improved accuracy but may not conform to sRGB standards
	elif s <= 0.04045:
		return s / 12.92
	elif s < 1.0:
		return ((s + 0.055) / 1.055) ** 2.4
	else:
		return 1.0
	
def l2s(l):
	if l <= 0.0:
		return 0.0
#	elif l <= 0.00313066844250063: # improved accuracy but may not conform to sRGB standards
	elif l <= 0.00313080:
		return l * 12.92
	elif l < 1.0:
		return ((l ** (1.0 / 2.4)) * 1.055) - 0.055
	else:
		return 1.0
	
def srgb2linear(rgba):
	# Convert RGB values (not Alpha)
	for i in range(3):
		rgba[i] = s2l(rgba[i])
	return rgba

def linear2srgb(rgba):
	# Convert RGB values (not Alpha)
	for i in range(3):
		rgba[i] = l2s(rgba[i])
	return rgba



###########################################################################
# User preferences and UI rendering class

class RenderLottiePreferences(bpy.types.AddonPreferences):
	bl_idname = __name__
	
	proxy_resolutionMultiplier: bpy.props.IntProperty(
		name="Resolution Multiplier",
		description="Render engine to use for proxy renders",
		default=100)
	
	def draw(self, context):
		layout = self.layout
		layout.label(text="Addon Default Preferences")



###########################################################################
# UI rendering classes

def vf_prepend_menu_renderLottie(self,context):
	try:
		layout = self.layout
		layout.operator(VF_renderLottie.bl_idname, text="Render Lottie JSON", icon='FILE') # RENDER_ANIMATION
	except Exception as exc:
		print(str(exc) + " | Error in Topbar Mt Render when adding to menu")



###########################################################################
# Addon registration functions

classes = (RenderLottiePreferences, VF_renderLottie)

addon_keymaps = []

def register():
	# register classes
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.TOPBAR_MT_render.prepend(vf_prepend_menu_renderLottie)
	# handle the keymap
	wm = bpy.context.window_manager
	kc = wm.keyconfigs.addon
	if kc:
		km = wm.keyconfigs.addon.keymaps.new(name='Screen Editing', space_type='EMPTY')
		kmi = km.keymap_items.new(VF_renderLottie.bl_idname, 'L', 'PRESS', ctrl=True, alt=True, shift=True)
		addon_keymaps.append((km, kmi))
	if kc:
		km = wm.keyconfigs.addon.keymaps.new(name='Screen Editing', space_type='EMPTY')
		kmi = km.keymap_items.new(VF_renderLottie.bl_idname, 'L', 'PRESS', oskey=True, alt=True, shift=True)
		addon_keymaps.append((km, kmi))

def unregister():
	# handle the keymap
	for km, kmi in addon_keymaps:
		km.keymap_items.remove(kmi)
	addon_keymaps.clear()
	# unregister classes
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
	bpy.types.TOPBAR_MT_render.remove(vf_prepend_menu_renderLottie)

if __name__ == "__main__":
	register()