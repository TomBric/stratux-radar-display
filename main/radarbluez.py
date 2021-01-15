import re
import pydbus
import logging
from espeakng import ESpeakNG

# DBus object paths
BLUEZ_SERVICE = 'org.bluez'
ADAPTER_PATH = '/org/bluez/hci0'

# global variables
bus = None
manager = None
adapter = None
esng = None
bluetooth_active = False
bt_devices = 0          # no of active bluetooth devices last time checked via connected devices


def bluez_init():
    global bus
    global manager
    global adapter
    global esng
    global bluetooth_active
    global bt_devices

    bus = pydbus.SystemBus()
    if bus is None:
        logging.debug("Systembus not received")
        return
    try:
        manager = bus.get(BLUEZ_SERVICE, '/')
        adapter = bus.get(BLUEZ_SERVICE, ADAPTER_PATH)
    except (KeyError, TypeError):
        logging.debug("BLUEZ-SERVICE not initialised")
        return
    esng = ESpeakNG(voice='en-us', pitch=30, speed=175)
    if esng is None:
        logging.info("INFO: espeak-ng not initialized")
        return
    connected_devices()     # check if already devices are connected
    if bt_devices > 0:
        esng.say("Stratux Radar connected")
        print("SPEAK: Stratux Radar connected")
    bluetooth_active = True


def speak(text):
    if bluetooth_active and bt_devices > 0:
        esng.say(text)
        logging.debug("Bluetooth speak"+text)


def connected_devices():
    global manager
    global bt_devices

    if not bluetooth_active:
        return
    managed_objects = manager.GetManagedObjects()
    r = re.compile('\/org\/bluez\/hci\d*\/dev_(.*)')
    # to match strings like /org/bluez/hci0/dev_58_C9_35_2F_A1_EF
    device_names = []
    for key, value in managed_objects.items():
        m = r.match(key)
        if m is not None:
            if 'org.bluez.Device1' in value:
                if value['org.bluez.Device1']['Connected']:
                    device_names.append(value['org.bluez.Device1']['Name'])
    bt_devices = len(device_names)
    return bt_devices, device_names
