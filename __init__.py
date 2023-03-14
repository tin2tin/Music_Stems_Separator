bl_info = {
    "name": "Music Stems Separator",
    "description": "Split music into stems",
    "author": "tintwotin",
    "version": (1, 0),
    "blender": (3, 40, 0),
    "location": "VSE > Sidebar > Audio > Music Stems Separator",
    "category": "Sequencer",
    "wiki_url": "",
    "tracker_url": "",
}

import bpy, os
import subprocess
from pathlib import Path


class AudioSeparationOperator(bpy.types.Operator):
    bl_idname = "audio.separate_stems"
    bl_label = "Separate Stems"

    @classmethod
    def poll(cls, context):
        return context.scene and context.scene.sequence_editor

    def execute(self, context):
        import site
        import sys

        app_path = site.USER_SITE
        if app_path not in sys.path:
            sys.path.append(app_path)
        pybin = sys.executable

        scene = context.scene
        audio_strip = scene.sequence_editor.active_strip

        if not audio_strip or audio_strip.type != "SOUND":
            self.report({"INFO"}, "No sound strip is the active strip.")
            print("No sound strip is the active strip.")
            return {"CANCELLED"}
        # Install Spleeter if needed
        try:
            from spleeter.separator import Separator
        except ModuleNotFoundError:
            print("Ensuring: pip")
            try:
                subprocess.call([pybin, "-m", "ensurepip"])
            except ImportError:
                pass
            self.report({"INFO"}, "Installing: spleeter module.")
            print("Installing: spleeter module")
            subprocess.check_call([pybin, "-m", "pip", "install", "spleeter"])
            try:
                from spleeter.separator import Separator
            except ModuleNotFoundError:
                print("Installation of the spleeter module failed")
                self.report(
                    {"INFO"},
                    "Installing spleeter module failed! Try to run Blender as administrator.",
                )
                return {"CANCELLED"}
        audio_file = os.path.abspath(audio_strip.sound.filepath)
        if not os.path.isfile(audio_file):
            self.report({"INFO"}, "The path of the source file needs to be absolute and not relative.")
            print("The path of the source file needs to be absolute and not relative.")
            return {"CANCELLED"}
        out_dir = os.path.dirname(audio_file)
        audio_file_clean = Path(audio_file).stem
        if not os.path.isdir(out_dir):
            os.mkdir(out_dir)
        num_stems = scene.audio_separation_properties.num_channels

        # Create the separator object
        separator = Separator(f"spleeter:{num_stems}stems")

        # Separate the audio track
        separator.separate_to_file(
            audio_file,
            out_dir,
            codec="mp3",
            filename_format="{filename}/{instrument}.{codec}",
        )

        # Add the separated stems as new sound strips in the VSE
        if int(num_stems) == 2:
            files = ["accompaniment", "vocals"]
        if int(num_stems) == 4:
            files = ["drums", "bass", "other", "vocals"]
        if int(num_stems) == 5:
            files = ["drums", "bass", "other", "piano", "vocals"]

        sequences = bpy.context.sequences
        channels = [s.channel for s in sequences]
        channels = sorted(list(set(channels)))
        empty_channel = channels[-1] + 1
        chan = empty_channel

        for i, item in enumerate(files):
            stem_file = os.path.join(
                f"{out_dir}", f"{audio_file_clean}", f"{files[i]}.mp3"
            )
            if os.path.isfile(stem_file):
                stem_strip = scene.sequence_editor.sequences.new_sound(
                    name=f"{files[i]}",
                    filepath=stem_file,
                    channel=i + empty_channel,
                    frame_start=int(audio_strip.frame_start),
                )
                stem_strip.frame_final_start = int(audio_strip.frame_final_start)
                stem_strip.frame_final_end = int(
                    audio_strip.frame_final_start + audio_strip.frame_final_duration
                )
        return {"FINISHED"}


class AudioSeparationPanel(bpy.types.Panel):
    bl_label = "Music Stem Separator"
    bl_idname = "AUDIO_PT_separation"
    bl_space_type = "SEQUENCE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Audio"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row()
        row.prop(scene.audio_separation_properties, "num_channels")

        row = layout.row()
        row.operator("audio.separate_stems")


class AudioSeparationProperties(bpy.types.PropertyGroup):
    num_channels: bpy.props.EnumProperty(
        name="Number of channels",
        description="Number of channels to split the audio into",
        items=[
            ("2", "2", "Split audio into 2 channels"),
            ("4", "4", "Split audio into 4 channels"),
            ("5", "5", "Split audio into 5 channels"),
        ],
    )


def register():
    bpy.utils.register_class(AudioSeparationOperator)
    bpy.utils.register_class(AudioSeparationPanel)
    bpy.utils.register_class(AudioSeparationProperties)

    bpy.types.Scene.audio_separation_properties = bpy.props.PointerProperty(
        type=AudioSeparationProperties
    )


def unregister():
    bpy.utils.unregister_class(AudioSeparationOperator)
    bpy.utils.unregister_class(AudioSeparationPanel)
    bpy.utils.unregister_class(AudioSeparationProperties)

    del bpy.types.Scene.audio_separation_properties


if __name__ == "__main__":
    register()
