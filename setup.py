import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
# "packages": ["os"] is used as example only
packages = ["os", "json", "traceback", "openvr", "sys", "time", "ctypes", "argparse", "pythonosc"]
exclude = ["tkinter", "asyncio", "concurrent", "html", "http", "lib2to3", "multiprocessing", "test", "unittest", "xmlrpc"]
file_include = ["config.json", "ovrConfig.json", "Run Debug Mode.bat", "openvr/", "bindings/", "app.vrmanifest"]
bin_excludes = ["_bz2.pyd", "_decimal.pyd", "_hashlib.pyd", "_lzma.pyd", "_queue.pyd", "_ssl.pyd", "libcrypto-1_1.dll", "libssl-1_1.dll", "ucrtbase.dll", "VCRUNTIME140.dll"]

build_exe_options = {"packages": packages, "excludes": exclude, "include_files": file_include, "bin_excludes": bin_excludes}

setup(
    name="knuckles_to_osc",
    version="0.1",
    description="Knuckles to OSC",
    options={"build_exe": build_exe_options},
    executables=[Executable("knuckles_to_osc.py", targetName="Knuckles_to_OSC.exe", base=False, icon="icon.ico")],
)