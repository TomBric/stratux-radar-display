import re
import pydbus

# DBus object paths
BLUEZ_SERVICE = 'org.bluez'
ADAPTER_PATH = '/org/bluez/hci0'


bus = None
manager = None
adapter = None


def bluez_init():
    global bus
    global manager
    global adapter

    bus = pydbus.SystemBus()
    manager = bus.get(BLUEZ_SERVICE, '/')
    adapter = bus.get(BLUEZ_SERVICE, ADAPTER_PATH)


def connected_devices():
    global manager

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
    return len(device_names), device_names
