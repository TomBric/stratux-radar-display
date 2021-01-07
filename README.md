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

   
   ## Software Installation Instructions (will follow)
