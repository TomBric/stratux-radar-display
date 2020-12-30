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
