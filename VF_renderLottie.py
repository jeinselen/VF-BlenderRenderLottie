bl_info = {
	"name": "VF Render Lottie",
	"author": "John Einselen",
	"version": (0, 7, 2),
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
		position_precision = scene.vf_render_lottie_settings.position_precision
		color_precision = scene.vf_render_lottie_settings.color_precision
		position_frames = scene.vf_render_lottie_settings.position_frames
		color_frames = scene.vf_render_lottie_settings.color_frames
		fill_color_string = scene.vf_render_lottie_settings.fill_color_string
		stroke_color_string = scene.vf_render_lottie_settings.stroke_color_string
		stroke_width_string = scene.vf_render_lottie_settings.stroke_width_string
		
		# Get active camera
		cam = scene.camera
		
		# Get depsgraph
		deps = context.evaluated_depsgraph_get()
		
		# Get active object
		obj = context.active_object
		
		# Get file path
		if self.filepath:
#			print("self.filepath: ", self.filepath)
			filepath = self.filepath
		else:
			filepath = scene.render.filepath
		
		# Support VF Autosave Render + Output Variables if plugin is installed and enabled
		if context.preferences.addons['VF_autosaveRender']:
			# Filter output file path if enabled
			if context.preferences.addons['VF_autosaveRender'].preferences.render_output_variables:
				# Check if the serial variable is used
				if '{serial}' in filepath:
					filepath = filepath.replace("{serial}", format(scene.autosave_render_settings.output_file_serial, '04'))
					scene.autosave_render_settings.output_file_serial += 1
				
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
				
				# Get fill color data as array (Color object created when adding shape or keyframes)
				if (fill_color_string in mesh.attributes):
					rgb = linear2srgb(mesh.attributes[fill_color_string].data[pi].color)
					# Replace with reduced precision array
					rgb = [round(rgb[0], color_precision), round(rgb[1], color_precision), round(rgb[2], color_precision)]
				else:
					rgb = [1.0, 1.0, 1.0]
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
					
					# Store references in dictionaries
					paths_dict[pi] = path
					fills_dict[pi] = fill
					
					# Initialise history data
					bez_hist.append(bez_arr)
					bez_frame.append(frame)
					rgb_hist.append(rgb_arr)
					rgb_frame.append(frame)
				
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
				
				# Update history references
				bez_hist[pi] = bez_arr
				rgb_hist[pi] = rgb_arr
				
				# Remove temp variables
				del path, fill, bez, bez_arr, rgb, rgb_arr
		
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

#class RenderLottiePreferences(bpy.types.AddonPreferences):
#	bl_idname = __name__
#	
#	proxy_resolutionMultiplier: bpy.props.IntProperty(
#		name="Resolution Multiplier",
#		description="Render engine to use for proxy renders",
#		default=100)
#	
#	def draw(self, context):
#		layout = self.layout
#		layout.label(text="Addon Default Preferences")



###########################################################################
# Project settings and UI rendering class

class RenderLottieSettings(bpy.types.PropertyGroup):
	# Precision Variables
	position_precision: bpy.props.IntProperty(
		name="Position",
		description="Pixel coordinate decimal places (lower values = smaller files)",
		default=1,
		step=1,
		soft_min=1,
		soft_max=4,
		min=0,
		max=8)
	color_precision: bpy.props.IntProperty(
		name="Color",
		description="RGB value decimal places (lower values = smaller files)",
		default=3,
		step=1,
		soft_min=2,
		soft_max=6,
		min=0,
		max=8)
	
	# Keyframe Variables
	position_frames: bpy.props.IntProperty(
		name="Position",
		description="Keyframe spacing (higher values = smaller files)",
		default=2,
		step=1,
		soft_min=1,
		soft_max=10,
		min=0,
		max=30)
	color_frames: bpy.props.IntProperty(
		name="Color",
		description="Keyframe spacing (higher values = smaller files)",
		default=2,
		step=1,
		soft_min=1,
		soft_max=10,
		min=0,
		max=30)
	
	# Attribute Strings
	fill_color_string: bpy.props.StringProperty(
		name="Fill Color",
		description="Attribute name that controls polygon face fill color",
		default="Lottie_Fill_Color",
		maxlen=256)
	stroke_color_string: bpy.props.StringProperty(
		name="Stroke Color",
		description="Attribute name that controls edge stroke color",
		default="Lottie_Stroke_Color",
		maxlen=256)
	stroke_width_string: bpy.props.StringProperty(
		name="Stroke Width",
		description="Attribute name that controls edge stroke width",
		default="Lottie_Stroke_Width",
		maxlen=256)

class RENDER_PT_render_lottie_panel(bpy.types.Panel):
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = "render"
	bl_category = 'Lottie'
	bl_label = "Lottie"
#	bl_idname = 'RENDER_PT_render_lottie_panel'
	bl_order = 100
	
	@classmethod
	def poll(cls, context):
		return True
	
	def draw(self, context):
		layout = self.layout
		layout.use_property_decorate = False  # No animation
		layout.use_property_split = True
		
		layout.label(text='Value Precision')
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=True, align=False)
		flow.prop(context.scene.vf_render_lottie_settings, 'position_precision')
		flow.prop(context.scene.vf_render_lottie_settings, 'color_precision')
		
		layout.label(text='Keyframe Spacing')
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=True, align=False)
		flow.prop(context.scene.vf_render_lottie_settings, 'position_frames')
		flow.prop(context.scene.vf_render_lottie_settings, 'color_frames')
		
		layout.label(text='Attribute Names')
		flow = layout.grid_flow(row_major=True, columns=0, even_columns=True, even_rows=True, align=False)
		flow.prop(context.scene.vf_render_lottie_settings, 'fill_color_string')
		flow.prop(context.scene.vf_render_lottie_settings, 'stroke_color_string')
		flow.prop(context.scene.vf_render_lottie_settings, 'stroke_width_string')
		
		layout.separator()
		
		layout.operator(VF_renderLottie.bl_idname, text='Render Lottie JSON', icon='FILE') # RENDER_ANIMATION



###########################################################################
# UI rendering classes

def vf_prepend_menu_renderLottie(self,context):
	try:
		layout = self.layout
		layout.operator(VF_renderLottie.bl_idname, text='Render Lottie JSON', icon='FILE') # RENDER_ANIMATION
	except Exception as exc:
		print(str(exc) + " | Error in Topbar Mt Render when adding to menu")



###########################################################################
# Addon registration functions

# Removed: RenderLottiePreferences
classes = (VF_renderLottie, RenderLottieSettings, RENDER_PT_render_lottie_panel)

addon_keymaps = []

def register():
	# register classes
	for cls in classes:
		bpy.utils.register_class(cls)
	# Settings reference
	bpy.types.Scene.vf_render_lottie_settings = bpy.props.PointerProperty(type=RenderLottieSettings)
	# Render menu button
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
	# Settings reference
	del bpy.types.Scene.vf_render_lottie_settings
	# Render menu button
	bpy.types.TOPBAR_MT_render.remove(vf_prepend_menu_renderLottie)

if __name__ == "__main__":
	register()