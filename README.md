# stratux-radar-display
Implementation of a standalone Radar display for Stratux Europe Edition. Can run on a separate Raspberry (e.g. Zero WH). Reads the aircraft data from Stratux and displays them on the specified display. The newest version now has a user interface include. You can connect 3 pushbottons to the device and use them for changing the radar radius, the height difference and sound options. A clock with a stop and lap timer, a g-meter, an artificial horizon and a compass (based on GPS) are also implemented.

Current supported displays are:
- Oled Display 1.5 inch (waveshare)
- Epaper Display 3.7 inch (waveshare)

More displays can be integrated.
You can find 3D printer files for cases of both variants in the repo (no-code). The Oled-case is designed for a 2 1/4 inch mounting hole, the E-paper case is designed for a 3 1/8 inch (80 mm) mounting hole. 

Usage:   
- python3 radar.py -d <DeviceName> [-s] -c <Stratux IP>
- runs radar application using DeviceName as display. -s indicates to use bluetooth for sound output. -c is the ip address of the Stratux to connect to (default is 192.168.10.1)
- Example: python3 radar.py -d Oled_1in5 -s -c 192.168.10.20

Find below a photo of the current supported displays
- the oled display is relatively small, but can be build into a 2 1/4" or larger instrument mounting hole
- the epaper display is larger and has optimal readability in sunlight. As e-paper it has a slower update of approx. twice per second. For the radar display this update rate is appropriate

![Display photo](https://github.com/TomBric/stratux-radar-display/blob/main/no-code/images/StratuxRadar.jpg)

## Hardware-List
- Raspberry Hardware: Since the code is pure python, no special hardware is required. I recommend a current "raspbian standard desktop os" as operating system. Performance requirements are not so high, so I recommend a "Rasperry Zero WH 512MByte RAM". Normal Raspberry 3B or 4 are also possible (but not tested by me). The Raspi Zero has the smallest form factor and best battery consumption. 
- Epaper-Display: Waveshare 18057 3.7inch e-Paper HAT: Directly mountable on the Raspi as a HAT.
Alternatively Waveshare 18381 3.7inch e-Paper Display + Waveshare Universal e-Paper Raw Panel Driver HAT 13512. The advantage of the latter is a better form factor for mounting it into some cases. Please make sure to switch the "Display Config" switch to A.

![Epaper photo](https://github.com/TomBric/stratux-radar-display/blob/main/no-code/images/Epaper_3in7.jpg)

- Oled-Display: Waveshare 14747, 128x128, General 1.5inch RGB OLED display Module
   ![Oled photo](https://github.com/TomBric/stratux-radar-display/blob/main/no-code/images/Oled_1in5.jpg)
   
 # Hardware connection of the OLED 1.5 inch display
 
| Connection  | PIN# on Raspberry  | Cable color |
|:-----------:|:------------------:|:-----------:|
| VCC | 17 | red |
| GND | 20 | black |
| DIN/MOSI | 19 | blue |
| CLK/SCK | 23| yellow  |
| CS/CE0 | 24 | orange |
| DC | 18 | green |
| RST | 22 | white |

# Hardware connection of the Epaper 3.7 inch display (if not using the hat version)
 
| Connection  | PIN# on Raspberry  |
|:-----------:|:------------------:|
| VCC | 17 |
| GND | 20 | 
| DIN/MOSI | 19 |
| CLK/SCK | 23|
| CS/CE0 | 24 |
| DC | 22 | 
| RST | 11 |
| BUSY | 18 |

Remark: If you have a barometric sensor or ahrs connected you may have conflict with GPIO Pin 11. 
You can also use PIN 16 (GPIO 23) for the RST line.

To do that please modify in /home/pi/stratux-radar-display/main/displays/Epaper_3in7/epdconfig.py line 38/39:
```
   # RST_PIN         = 17    # if directly as hat
   RST_PIN = 23  # for cable mounted in stratux on different GPIO 23, which is PIN 16
```

# Hardware connection of the pushbuttons for the user interface
 
| Pushbutton  | PIN# on Raspberry  |
|:-----------:|:------------------:|
| Left | 37 |
| Middle | 38 | 
| Right | 40 | 

All pushbuttons are used as pull down. Connect the other side of all buttons to GND (PIN39).
   
   ## Software Installation Instructions
   ### Standard setup
   1. Download the image under Releases/Assets to your local computer. Image with "oled" is preconfigured for the Oled 1.5 inch display. Image with epaper is the version for the waveshare 3.7 inch epaper displays. Both version will support Bluetooth
   2. Flash the image using Balena/Etcher or Win32DiskImager or Raspberry Pi Imager to your SD card (at least 8GB)
   3. Insert the SD into you raspberry and let it boot. It should automatically startup and connect to the Stratux-Europe edition. 
   Remark: Current configuration is for Stratux-Europe on IP address 192.168.10.1. If you have a different configuration please update /home/pi/image/stratux_radar.sh accordingly.
   
   ### Expert setup 
   1. Configure a clean Raspbian buster installation on your SD card. E.g. using Raspberry Pi Imager. Recommended image is "Raspbian Pi OS 32 lite". If you want to integrate bluetooth sound output, please user "Raspian Pi OS desktop". Unfortunately bluetooth is not properly installed in the buster lite release.
   2. For network configuration: Create empty file named "ssh" on the boot partition. Copy "wpa_supplicant.conf" on the boot partition as well. This well enable the Pi to connect to the Stratux and also enable ssh connection.
   3. The file "wpa_supplicant.conf" is actually configured for the network "stratux". If you want a different network setup please modify "wpa_supplicant.conf" accordingly. To get the following configurations please setup network and keys in "wpa_supplicant.conf" so that you have internet connection.
   4. Startup your Stratux and boot your new raspberry. Figure out the IP-adress of your raspberry, e.g. by checking in the logs of your WLAN router (or use arp requests)
   5. From your workstation open a remote shell on the new raspberry:  ssh pi@192.168.x.x. Password is standard for the pi.
   6. Copy the configuration script (under github/image) onto the radar-raspberry:  scp configure_radar.sh pi@192.168.x.x:/home/pi
   7. Execute the configuration script as user pi. "/bin/bash configure_radar.sh".  This will take some time since it does an update on the pi. It will also clone a version of the radar into /home/pi/stratux-radar-display
   8. Depending on your display modify /home/pi/stratux-radar-display/image/stratux_radar.sh. In paramater "-c" enter the IP address of your stratux and in parameter "-d" the device. E.g.
         - cd /home/pi/stratux-radar-display/main && python3 radar.py -s -d Oled_1in5 -c 192.168.10.1 &            
         - cd /home/pi/stratux-radar-display/main && python3 radar.py -s -d Epaper_3in7 -c 192.168.178.55 & 
   9. The configuration skript will make an entry in crontab of user pi, so that radar will start automatically after reboot.

   
   ### Installation on a standard stratux device
   stratux-radar-display can run also directly on your stratux device. Connect the displays to the GPIO pins of the Stratux. 
   Installation is only for expert users! To install the software perform the following steps:
   
   1. Connect your stratux to a network, e.g. by integrating into your WLAN: Logon as root on your stratux. Make a copy of the existing /etc/network/interfaces (e.g. cp /etc/network/interfaces /etc/network/interfaces.stratux) and modify /etc/network/interfaces, so that it looks like
   ```
    auto lo
    iface lo inet loopback
    allow-hotplug eth0
    iface eth0 inet dhcp
    allow-hotplug wlan0

    iface wlan0 inet dhcp
       wpa-ssid "<YOUR WLAN SSID AT HOME>"
       wpa-psk "<YOUR WLAN WPA PSK FROM HOME>"  
   ```
   This will connect your stratux to your local wlan. Alternatively connect Stratux via network cable.
   
   2. Reboot and log on to your Stratux as user pi, directory /home/pi
    Clone the stratux repository by "git clone https://github.com/TomBric/stratux-radar-display.git"
   3. Execute the configuration skript: "/bin/bash stratux-radar-display/image/configure_radar_on_stratux.sh"
   4. Configure the startup skript "image/stratux-radar.sh": remove the option "-s" and use the corresponding display option with "-d Oled_1in5" or "-d Epaper_3in7"
   5. Restore the original /etc/network/interfaces (e.g. by "mv /etc/network/interfaces.stratux /etc/network/interfaces")
   6. Reboot stratux. If everything if installed correctly, the display software will automatically startup.

The Oled display uses different GPIO-Pins as the baro-sensor, so there is no conflict. Also the e-Paper display can be connected (not the HAT version) with the baro and ahrs sensors in place.
   Remark: Bluetooth is currently not properly supported by Stratux, so if you want audio output to your headset, please use Raspian OS Desktop on a Raspberry ZeroWH.
   
   
   ### Bluetooth devices
   
   stratux-radar-display will automatically connect the your headset if their bluetooth is switched on. 
   But once you need to do the pairing of a new bluetooth device. 
   
   There are two options for pairing:
   
   **Option 1: Directly on the device via buttons:**
   
   * Change to Status-Mode (long press middle button, to change from Radar-> Timer -> AHRS -> Status)
   * Press "scan" (right button). The display now scans 30 secs for new devices. Set your headset as visible and it will be detected (For Bose A20 this is a 5 second press on the Bluetooth-Button until it flashes blue-red)
   * A list of detected devices is shown, press "yes" for the detected device
      
   **Option 2: via ssh and bluetoothctl**
   
   * Logon on your radar as user pi:  ssh pi@192.168.x.x
   * Start bluetoothctl:   
   ```
      -> bluetoothctl
      -> scan on      set your device in pairing mode (for Bose A20, do a 5 sec press on the bluetooth button until it flashes magenta)
      -> wait till your device is displayed, this will look like:  
            [NEW] Device 04:52:C7:02:C0:01 Bose A20,              04:52:C7:02:C0:01 is the device id, which will be different for you
      -> scan off
      -> trust <device-id>   <replace with your device id>
      -> pair <device-id>, eventually your pin is requested (for Bose A20 enter "0000")
      -> connect <device-id>
   If everything works fine, the pi displays connected and your device name.
      -> exit
   ```
   
   The bluetooth configuration is now ready and each time the radar has your device in reachability, it will connect. On the display the bluetooth symbol will be visible in the right corner.
   
 # Manual of stratux-radar-display (user interface with 3 pushbuttons) (thanks SiggiS)
### In all screen modes:
   - middle button (>1 sec): switch to next mode (radar -> timer -> ahrs -> radar)
   - left button (>1 sec): start shutdown, press any other button to cancel shutdown
   - after shutdown, display can be reactivated by switching on/off
   
### Radar screen mode:
   - left button short: change radar range (2nm -> 5nm -> 10nm -> 40nm)
   - middle button short: enable/disable sound (if bluetooth speaker/headset is connected)
   - right button short: change height difference for traffic (1000ft -> 2000 ft -> 5000 ft -> 10k ft -> 50k ft)
   - right button long: screen refresh. This is relevant for Epaper only since it becomes "dirty" over time with partial refresh.
     
![Radar](https://github.com/TomBric/stratux-radar-display/blob/main/no-code/images/Epaper-Radar-Mode.jpg)

Recommended setting for normal piston aircraft is 5 nm and 2000 ft.

### Timer screen mode:
   - right button short:  start or stop timer (displayed in the middle)
   - left button short: start lap-timer (displayed on bottom)
   - middle short: change to countdown-setting. Here a countdown timer can be set. If the countdown runs down to 0:00, this will also be signalled by sound output in your headset
   - press middle short again to end countdown-setting. Countdown will be started, wenn timer is started. It timer is already running, countdown will start as soon as you leave the countdown setting mode

   - in countdown-setting mode:
      - press middle short again to end countdown-setting. Countdown will be started, wenn timer is started. It timer is already running, countdown will start as soon as you leave the countdown setting mode
      - press left button to increase countdown time by 10 mins
      - press right button to increase countdown time by 1 mins
      - max countdown time is 2 hours. If you set countdown time > 2 h, countdone timer will be cleared

    
![Timer](https://github.com/TomBric/stratux-radar-display/blob/main/no-code/images/Epaper-TimerMode.jpg)

 ### AHRS mode:
 - no special interaction, press long middle for next mode

![AHRS](https://github.com/TomBric/stratux-radar-display/blob/main/no-code/images/Epaper-AHRS-Mode.jpg)

### G-Meter mode:
    - press short right to reset min and max values
    - press long middle for next mode

![Gmeter](https://github.com/TomBric/stratux-radar-display/blob/main/no-code/images/Epaper-G-Meter-Mode.jpg)

### Compass mode:
    - press long middle for next mode

![Compass](https://github.com/TomBric/stratux-radar-display/blob/main/no-code/images/Epaper-CompassMode.jpg)

# Shell command parameters
```
  usage: radar.py [-h] -d DEVICE [-s] [-t] [-a] [-x] [-g] [-o] [-c CONNECT] [-v]
                [-r]

Stratux web radar for separate displays

optional arguments:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        Display device to use
  -s, --speak           Speech warnings on
  -t, --timer           Start mode is timer
  -a, --ahrs            Start mode is ahrs
  -x, --status          Start mode is status
  -g, --gmeter          Start mode is g-meter
  -o, --compass         Start mode is compass
  -c CONNECT, --connect CONNECT
                        Connect to Stratux-IP
  -v, --verbose         Debug output on
  -r, --registration    Display registration no   
  
  
Example:
python3 main/radar.py -d Epaper_3in7 -c 192.168.10.1 -r -s

  ```

