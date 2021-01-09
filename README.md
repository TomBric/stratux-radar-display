# stratux-radar-display
Implementation of a standalone Radar display for Stratux Europe Edition. Can run on a separate Raspberry (e.g. Zero W). Reads the aircraft data from Stratux and displays them on the specified display. 

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
- Raspberry Hardware: Since the code is pure python, no special hardware is required. I recommend a current raspbian lite as operating system. Performance requirements are not so high, so I recommend a "Rasperry Zero WH 512MByte RAM". Normal Raspberry 3B or 4 are also possible (but not tested by me). The Raspi Zero has the smallest form factor and best battery consumption. 
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

   
   ## Software Installation Instructions
   ### Expert setup 
   1. Configure a clean Raspbian buster installation on your SD card. E.g. using Raspberry Pi Imager. Recommended image is "Raspbian Pi OS 32 lite"
   2. For network configuration: Create empty file "ssh" on the boot partition. Copy "wpa_supplicant.conf" on the boot partition as well. This well enable the Pi to connect to the Stratux and also enable ssh connection. The file "wpa_supplicant.conf" is configured for the network "stratux". If you want a different network setup please modify "wpa_supplicant.conf" accordingly.
   3. Startup your Stratux and boot your new raspberry. The new raspberry should connect as 192.168.10.10 or .11 or .12 to the stratux network.
   4. From your workstation open a remote shell on the new raspberry:  ssh pi@192.168.10.x. Password is standard for the pi.
   5. On the raspberry modify the following settings via "sudo raspi-config":   "-> Interface Options -> Enable SPI"
   6. Copy the configuration script (under github/image) onto the radar-raspberry:  scp configure_radar.sh pi@192.168.10.10:/home/pi
   7. Execute the configuration script as root. "/bin/bash configure_radar.sh".  This will take some time since it does an update on the pi. It will also clone a version of the radar into /root/stratux-radar-display
   8. Depending on your display copy from /root/stratux-radar-display/image:  "rc.local.Oled_1in5" or "rc.local.Epaper_3in7"to /etc/rc.local. This will make the pi to automatically startup the radar software.
   Remark: Raspbian Buster on the Pi Zero has problems with IPV6. So if you connect it to some network with IPV6 devices, make sure IPV6 is disabled (append ipv6.disable=1 on the first line in cmdline.txt in the image before booting)
   
   ### Standard setup
   1. Download the image under Releases/Assets to your local computer. Image with "oled" is preconfigured for the Oled 1.5 inch display. Epaper-Versions will follow.
   2. Flash the image using Balena/Etcher or Win32DiskImager or Raspberry Pi Imager to your SD card (at least 8GB)
   3. Insert the SD into you raspberry and let it boot. It should automatically startup and connect to the Stratux-Europe edition. Remark: Current configuration is for Stratux-Europe on IP address 192.168.10.1. If you have a different configuration please update /etc/rc.local accordingly.
