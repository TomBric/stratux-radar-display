# stratux-radar-display
Implementation of a standalone Radar display for Stratux Europe Edition. Can run on a separate Raspberry (e.g. Zero WH). Reads the aircraft data from Stratux and displays them on the specified display. The newest version now has a user interface include. You can connect 3 pushbottons to the device and use them for changing the radar radius, the height difference and sound options. A clock with a stop and lap timer is also implemented.

Current supported displays are:
- Oled Display 1.5 inch (waveshare)
- Epaper Display 3.7 inch (waveshare)

More displays can be integrated.

Usage:   
- python3 radar.py -d <DeviceName> [-s] -c <Stratux IP>
- runs radar application using DeviceName as display. -s indicates to use bluetooth for sound output. -c is the ip address of the Stratux to connect to (default is 192.168.10.1)
- Example: python3 radar.py -d Oled_1in5 -s -c 192.168.10.20

Find below a photo of the current supported displays
- the oled display is relatively small, but can be build into a 2 1/4" or larger instrument mounting hole
- the epaper display is larger and has optimal readability in sunlight. As e-paper it has a slower update of approx. once per second
![Display photo](https://github.com/TomBric/stratux-radar-display/blob/main/StratuxRadar.jpg)

## Hardware-List
- Raspberry Hardware: Since the code is pure python, no special hardware is required. I recommend a current "raspbian standard desktop os" as operating system. Performance requirements are not so high, so I recommend a "Rasperry Zero WH 512MByte RAM". Normal Raspberry 3B or 4 are also possible (but not tested by me). The Raspi Zero has the smallest form factor and best battery consumption. 
- Epaper-Display: Waveshare 18057 3.7inch e-Paper HAT: Directly mountable on the Raspi as a HAT.
Alternatively Waveshare 18381 3.7inch e-Paper Display + Waveshare Universal e-Paper Raw Panel Driver HAT 13512. The advantage of the latter is a better form factor for mounting it into some cases. Please make sure to switch the "Display Config" switch to A.

![Epaper photo](https://github.com/TomBric/stratux-radar-display/blob/main/Epaper_3in7.jpg)

- Oled-Display: Waveshare 14747, 128x128, General 1.5inch RGB OLED display Module
   ![Oled photo](https://github.com/TomBric/stratux-radar-display/blob/main/Oled_1in5.jpg)
   
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
   Remark: Current configuration is for Stratux-Europe on IP address 192.168.10.1. If you have a different configuration please update /home/pi/image/start_radar.sh accordingly.
   
   ### Expert setup 
   1. Configure a clean Raspbian buster installation on your SD card. E.g. using Raspberry Pi Imager. Recommended image is "Raspbian Pi OS 32 lite". If you want to integrate bluetooth sound output, please user "Raspian Pi OS desktop". Unfortunately bluetooth is not properly installed in the buster lite release.
   2. For network configuration: Create empty file named "ssh" on the boot partition. Copy "wpa_supplicant.conf" on the boot partition as well. This well enable the Pi to connect to the Stratux and also enable ssh connection.
   3. The file "wpa_supplicant.conf" is actually configured for the network "stratux". If you want a different network setup please modify "wpa_supplicant.conf" accordingly. To get the following configurations please setup network and keys in "wpa_supplicant.conf" so that you have internet connection.
   4. Startup your Stratux and boot your new raspberry. Figure out the IP-adress of your raspberry, e.g. by checking in the logs of your WLAN router (or use arp requests)
   5. From your workstation open a remote shell on the new raspberry:  ssh pi@192.168.x.x. Password is standard for the pi.
   6. On the raspberry modify the following settings via "sudo raspi-config":   "-> Interface Options -> Enable SPI"
   7. Copy the configuration script (under github/image) onto the radar-raspberry:  scp configure_radar.sh pi@192.168.x.x:/home/pi
   8. Execute the configuration script as user pi. "/bin/bash configure_radar.sh".  This will take some time since it does an update on the pi. It will also clone a version of the radar into /home/pi/stratux-radar-display
   9. Depending on your display modify /home/pi/stratux-radar-display/image/stratux_radar.sh. In paramater "-c"Enter the IP Adress of your stratux and in parameter "-d" the device. E.g.
         - cd /home/pi/stratux-radar-display/main && python3 radar.py -s -d Oled_1in5 -c 192.168.10.1 &            
         - cd /home/pi/stratux-radar-display/main && python3 radar.py -s -d Epaper_3in7 -c 192.168.178.55 & 
    10. The configuration skript will make an entry in crontab of user pi, so that radar will start automatically after reboot.

   Remark: Raspbian Buster on the Pi Zero has problems with IPV6. So if you connect it to some network with IPV6 devices, make sure IPV6 is disabled (append ipv6.disable=1 on the first line in cmdline.txt in the image before booting)
   
   ### Installation on a standard stratux device
   stratux-radar-display can run also directly on your stratux device. Connect the displays to the GPIO pins of the Stratux. You can then start with step 5 from expert setup above. The Oled display uses different GPIO-Pins as the baro-sensor, so there is no conflict. Also the e-Paper display can be connected (not the HAT version) with the baro and ahrs sensors in place.
   Remark: Bluetooth is currently not properly supported by Stratux, so if you want audio output to your headset, please use Raspian OS Desktop on a Raspberry ZeroWH.
   
   
   ### Bluetooth devices
   
   stratux-radar-display will automatically connect the your headset if their bluetooth is switched on. 
   But once you need to do the pairing of a new bluetooth device. To do that:
   1. Logon on your radar as user pi:  ssh pi@192.168.x.x
   2. Start bluetoothctl:   
   ```
      -> bluetoothctl
      -> scan on      set your device in pairing mode (for Bose A20, do a long press on the bluetooth button until it flashes magenta)
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
   
   
