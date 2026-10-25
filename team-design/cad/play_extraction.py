"""Start playback after the Blender GUI opens the prepared scene."""
import bpy
def play():
    bpy.context.scene.frame_set(1)
    if bpy.context.screen and not bpy.context.screen.is_animation_playing:
        bpy.ops.screen.animation_play()
    return None
bpy.app.timers.register(play, first_interval=1.0)
