import os
import sys
import argparse
import ctypes
import json
import collections
import time
import traceback
from types import SimpleNamespace

import openvr
from pythonosc import udp_client


parser = argparse.ArgumentParser(description="Knuckles to OSC: Relays your raw knuckles controller inputs through OSC")
parser.add_argument("--debug", required=False, action="store_true")
parser.add_argument("--ip", required=False, type=str, default=None)
parser.add_argument("--port", required=False, type=int, default=None)
parser.add_argument("--hz", required=False, type=float, default=None)
args = parser.parse_args()


DTYPES = SimpleNamespace(
    BOOL = "bool",
    VECTOR1 = "vector1",
    VECTOR2 = "vector2",
    SKELETON = "skeleton"
)
ControlAction = collections.namedtuple("ControlAction", ["dtype", "handle", "param"])

# Set window name on Windows
if os.name == 'nt':
    ctypes.windll.kernel32.SetConsoleTitleW("Knuckles to OSC")


def osc_compress_float(x):
    """For some reason VRChat slows to a crawl whenever I send it floats equal to zero, so we squeeze the value a little to avoid that"""
    return (x * 0.998) + 0.001


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def move(y, x):
    """Moves console cursor."""
    print("\033[%d;%dH" % (y, x))


def cls():
    """Clears Console"""
    os.system('cls' if os.name == 'nt' else 'clear')


CONFIG = json.load(open(resource_path('config.json')), object_hook=lambda x: SimpleNamespace(**x))
OVRCONFIG = json.load(open(resource_path('ovrConfig.json')), object_hook=lambda x: SimpleNamespace(**x))
IP = args.ip if args.ip is not None else CONFIG.ip
PORT = args.port if args.port is not None else CONFIG.port
HZ = args.hz if args.hz is not None else CONFIG.hz
FINGERS = {
    "Thumb": openvr.VRFinger_Thumb,
    "Index": openvr.VRFinger_Index,
    "Middle": openvr.VRFinger_Middle,
    "Ring": openvr.VRFinger_Ring,
    "Pinky": openvr.VRFinger_Pinky
}

SPLAYFINGERS = {
    "Index": openvr.VRFingerSplay_Thumb_Index,
    "Middle": openvr.VRFingerSplay_Index_Middle,
    "Ring": openvr.VRFingerSplay_Middle_Ring,
    "Pinky": openvr.VRFingerSplay_Ring_Pinky
}


def format_skeletal_summary(x):
    curls = ", ".join([f"{k} {x.flFingerCurl[v]: #.4f}" for k, v in FINGERS.items()])
    splays = ", ".join([f"{k} {x.flFingerSplay[v]: #.4f}" for k, v in SPLAYFINGERS.items()])
    return f"Curl: {curls} | Splay: {splays}"


osc = udp_client.SimpleUDPClient(IP, PORT)

app = openvr.init(openvr.VRApplication_Background)
action_path = os.path.join(resource_path(OVRCONFIG.bindings_folder), OVRCONFIG.action_manifest_file)
appmanifest_path = os.path.join(resource_path(OVRCONFIG.app_manifest_file))
openvr.VRApplications().addApplicationManifest(appmanifest_path)
openvr.VRInput().setActionManifestPath(action_path)
action_set_handle = openvr.VRInput().getActionSetHandle(OVRCONFIG.action_set_handle)

actions = {}
for item in CONFIG.outputs:
    if not item.send:
        continue

    a = {}
    action_name, a["dtype"] = getattr(OVRCONFIG.actions, item.name)
    a["handle"] = openvr.VRInput().getActionHandle(action_name)
    a["param"] = item.param
    actions[item.name] = ControlAction(**a)

def handle_input():
    actionsets = (openvr.VRActiveActionSet_t * 1)()
    actionsets[0].ulActionSet = action_set_handle
    openvr.VRInput().updateActionState(actionsets)

    if args.debug:
        move(7 + len(actions), 0)
    
    for name, action in actions.items():
        if action.dtype == DTYPES.BOOL:
            value = openvr.VRInput().getDigitalActionData(action.handle, openvr.k_ulInvalidInputValueHandle)
            if value.bChanged:
                osc.send_message(f"{CONFIG.osc_prefix}{action.param}", bool(value.bState))

            if args.debug:
                print(f"{name}: state = {value.bState}, changed = {value.bChanged}")
        elif action.dtype == DTYPES.SKELETON:
            value = openvr.VRInput().getSkeletalSummaryData(action.handle, openvr.VRSummaryType_FromDevice)
            for fname, fidx in FINGERS.items():
                osc.send_message(f"{CONFIG.osc_prefix}{action.param}/Curl/{fname}", osc_compress_float(value.flFingerCurl[fidx]))
            for fname, fidx in SPLAYFINGERS.items():
                osc.send_message(f"{CONFIG.osc_prefix}{action.param}/Splay/{fname}", osc_compress_float(value.flFingerSplay[fidx]))

            if args.debug:
                print(f"{name}: {format_skeletal_summary(value)}")
        else:
            value = openvr.VRInput().getAnalogActionData(action.handle, openvr.k_ulInvalidInputValueHandle)
            if action.dtype == DTYPES.VECTOR1:
                osc.send_message(f"{CONFIG.osc_prefix}{action.param}", float(value.x))

                if args.debug:
                    print(f"{name}: x = {value.x: #.4f}")
            elif action.dtype == DTYPES.VECTOR2:
                osc.send_message(f"{CONFIG.osc_prefix}{action.param}/X", osc_compress_float(value.x))
                osc.send_message(f"{CONFIG.osc_prefix}{action.param}/Y", osc_compress_float(value.y))
                
                if args.debug:
                    print(f"{name}: x = {value.x: #.4f}, y = {value.y: #.4f}")
    
    if args.debug:
        sys.stdout.flush()


cls()
print("Knuckles to OSC running...\n")
print(f"IP:\t\t{IP}")
print(f"Port:\t\t{PORT}")
print(f"Frequency:\t{HZ} hZ")
print("Outputs:")
print("\n".join([f"\t{k} -> {CONFIG.osc_prefix}{v.param}" for k, v in actions.items()]))
sys.stdout.flush()


while True:
    try:
        handle_input()
        time.sleep(1 / HZ)
    except KeyboardInterrupt:
        #cls()
        sys.exit()
    except Exception:
        #cls()
        print("UNEXPECTED ERROR\n")
        print("Please Create an Issue on GitHub with the following information:\n")
        traceback.print_exc()
        input("\nPress ENTER to exit")
        sys.exit()