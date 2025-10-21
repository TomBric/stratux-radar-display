

# stratux-radar-display
Implementation of a Radar display for Stratux Europe Edition. Can run on a separate Raspberry (e.g. Zero W or Zero 2 W) or directly with the display attached to your stratux.
Reads the aircraft data from Stratux and displays them on the specified display. You can connect 3 pushbuttons to the device and use them for changing the radar radius, the height difference and sound options. A clock with a stop and lap timer, an automatic flight-time measurement, a g-meter, an artificial horizon, a compass (based on GPS), a VSI display and other features are also implemented.

> [!NOTE]
> update in v2.06: stratux-radar-display now offers a web configuration interface. You can easily configure your settings, modes and other options with this web page. See software installation instructions.
> Other features have not been changed. If you are happy with your version, there is no need to update.


Current supported displays are:
- Oled Display 1.5 inch (waveshare)
- Epaper Display 3.7 inch (waveshare)
- Epaper Display 1.54 inch (waveshare)
- ST7789 controller based displays (LCD, 240x320 e.g. waveshare or Crystalfontz)

The best user experience is with the epaper-display. They are perfectly readable even in bright cockpits in the sun.

| 3.7 inch Epaper round for 80 mm instrument hole | 3.7 inch Epaper for 80 mm instrument hole |
|-------------------------------------------------|---------------------------------|
| ![3 7-Round](https://github.com/user-attachments/assets/ae222a08-6492-4109-afd7-b78ef93f96e0) | ![](https://github.com/TomBric/stratux-radar-display/blob/main/.github/images/All-in-one%20Epaper%201.jpg) |

| 1.54 inch Epaper for 57 mm instrument hole | Oled for 57 mm instrument hole | ST 7789 controller display |
|-------------------------|--------------------------------|----------------------------|
| ![](https://github.com/TomBric/stratux-radar-display/raw/main/.github/images/All-in-one%20OLED%205.jpg) |![2 0 LCD](https://github.com/user-attachments/assets/395df2c8-c7a5-4718-957e-17fd32838e0b) | ![](https://github.com/TomBric/stratux-radar-display/raw/main/.github/images/1.54-front-ahrs.jpg) |

- [Hardware and Wiring the displays](https://github.com/TomBric/stratux-radar-display/wiki/Hardware-and-wiring)
- [Connecting pushbuttons for a user interface](https://github.com/TomBric/stratux-radar-display/wiki/Connecting-pushbuttons-for-a-user-interface)
- [Software Installation](https://github.com/TomBric/stratux-radar-display/wiki/Installation)
  
- [Bluetooth and external sound](https://github.com/TomBric/stratux-radar-display/wiki/Bluetooth-and-external-sound)
- [Manual for user interface with 3 pushbuttons](https://github.com/TomBric/stratux-radar-display/wiki/Manual-for-user-interface-with-3-pushbuttons)


You can find instructions how to build the full instruments in the wiki. 
The Oled-case is designed for a 2 1/4 inch mounting hole, the E-paper case is designed for a 3 1/8 inch (80 mm) mounting hole. Instructions e.g. how to build an [all-in one 2 1/4 Oled case](https://github.com/TomBric/stratux-radar-display/wiki/All-in-one-aluminum-case-(Stratux-with-oled-display) "wiki 2 1/4"), or [all-in-one 3 1/8 Epaper instrument](https://github.com/TomBric/stratux-radar-display/wiki/All-in-one-aluminum-case-for-80-mm-instrument-hole-with-Epaper-display-and-Bluetooth "wiki 3 1/8"), or [Epaper 3 1/8 display only](https://github.com/TomBric/stratux-radar-display/wiki/Epaper-Display-for-80-mm-instrument-hole) can be found in the wiki.

Optional power supply suggestion: If you need a reliable display power supply in your airplane, I have good experiences with small step-down converters XL4015. Then you can use the aircraft power supply (up to 40V). Calibrate the XL4015 at home for a power output at 5 V e.g. using an old laptop power supply. XL4015 also work well for the stratux itself. If you encounter problems with radio noise, please ensure that the power cable to the display is twisted and if necessary use a ferrit-core at the power connection.  



