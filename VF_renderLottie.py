bl_info = {
	"name": "VF Render Lottie",
	"author": "John Einselen",
	"version": (0, 6, 0),
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
		float_position = 2
		float_color = 4
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
		layer.name = obj.name
		layer.width = width
		layer.height = height
		layer.size = Point(width, height)
		
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
				
				# Get path data
				bez = objects.Bezier()
				bez.close()
				for i in polygon.vertices:
					# Get world position (3D)
					wpos = obj.matrix_world @ mesh.vertices[i].co
					# Get render position (2D)
					rpos = bpy_extras.object_utils.world_to_camera_view(scene, cam, wpos)
					# Add point to path (Y is flipped)
					bez.add_point(Point(round(rpos.x * width, float_position), round((1.0 - rpos.y) * height, float_position)))
				
				# Get fill data
				rgba = mesh.attributes[fill_color_string].data[pi].color
				
				if (frame == start):
					# Create polygon group
					group = layer.add_shape(objects.Group())
					
					# Create path
					path = group.add_shape(objects.Path())
					path.shape.value = bez
					
					# Get color data and create fill
					fill = group.add_shape(objects.Fill(Color(round(rgba[0], float_color), round(rgba[1], float_color), round(rgba[2], float_color))))
				
				else:
					# Add keyframes
					path.shape.add_keyframe(frame, bez)
					fill.color.add_keyframe(frame, Color(round(rgba[0], float_color), round(rgba[1], float_color), round(rgba[2], float_color)))
		
		# Export Lottie JSON file
		export_lottie(an, filepath)
		
		# Reset timeline to original frame number
		scene.frame_set(frame_original)
		
		return {'FINISHED'}

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