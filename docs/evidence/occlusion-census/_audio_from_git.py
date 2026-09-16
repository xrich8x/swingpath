"""Load the shipped-then-cut backend/swingvision/audio.py from git WITHOUT restoring it
to the tree (qa never writes backend/). Pinned to 7570a2a^ = the last commit where it
shipped; invoked, never re-implemented."""
import subprocess, types, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
REV = "7570a2a^"
def load():
    src = subprocess.check_output(["git", "-C", ROOT, "show", f"{REV}:backend/swingvision/audio.py"])
    mod = types.ModuleType("audio_7570a2a_parent")
    mod.__file__ = f"git:{REV}:backend/swingvision/audio.py"
    exec(compile(src, mod.__file__, "exec"), mod.__dict__)
    return mod
