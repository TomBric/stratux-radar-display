
# stratux-radar-display
Implementation of a Radar display for Stratux Europe Edition. Can run on a separate Raspberry (e.g. Zero W or Zero 2 W) or directly with the display attached to your stratux.
Reads the aircraft data from Stratux and displays them on the specified display. You can connect 3 pushbuttons to the device and use them for changing the radar radius, the height difference and sound options. A clock with a stop and lap timer, an automatic flight-time measurement, a g-meter, an artificial horizon, a compass (based on GPS), a VSI display and other features are also implemented.


Current supported displays are:
- Oled Display 1.5 inch (waveshare)
- Epaper Display 3.7 inch (waveshare)
- Epaper Display 1.54 inch (waveshare)

The best user experience is with the epaper-display. They are perfectly readable even in bright cockpits in the sun

| 3.7 inch Epaper for 80 mm instrument hole      |      1.54 inch Epaper for 57 mm instrument hole | Oled for 57 mm instrument hole |
|---------------------------------|----------------------------|----------------|
| ![](https://github.com/TomBric/stratux-radar-display/blob/main/.github/images/All-in-one%20Epaper%201.jpg) | ![](https://github.com/TomBric/stratux-radar-display/raw/main/.github/images/1.54-front-ahrs.jpg) |  ![](https://github.com/TomBric/stratux-radar-display/raw/main/.github/images/All-in-one%20OLED%205.jpg) |



- [Hardware and Wiring the displays](https://github.com/TomBric/stratux-radar-display/wiki/Hardware-and-wiring)
- [Connecting pushbuttons for a user interface](https://github.com/TomBric/stratux-radar-display/wiki/Connecting-pushbuttons-for-a-user-interface)
- [Software Installation](https://github.com/TomBric/stratux-radar-display/wiki/Installation)


You can find instructions how to build the full instruments in the wiki. 
The Oled-case is designed for a 2 1/4 inch mounting hole, the E-paper case is designed for a 3 1/8 inch (80 mm) mounting hole. Instructions e.g. how to build an [all-in one 2 1/4 Oled case](https://github.com/TomBric/stratux-radar-display/wiki/All-in-one-aluminum-case-(Stratux-with-oled-display) "wiki 2 1/4"), or [all-in-one 3 1/8 Epaper instrument](https://github.com/TomBric/stratux-radar-display/wiki/All-in-one-aluminum-case-for-80-mm-instrument-hole-with-Epaper-display-and-Bluetooth "wiki 3 1/8"), or [Epaper 3 1/8 display only](https://github.com/TomBric/stratux-radar-display/wiki/Epaper-Display-for-80-mm-instrument-hole) can be found in the wiki.

Optional power supply suggestion: If you need a reliable display power supply in your airplane, I have good experiences with small step-down converters XL4015. Then you can use the aircraft power supply (up to 40V). Calibrate the XL4015 at home for a power output at 5 V e.g. using an old laptop power supply. XL4015 also work well for the stratux itself. If you encounter problems with radio noise, please ensure that the power cable to the display is twisted and if necessary use a ferrit-core at the power connection.  
   


   
### External Sound output
   
   You can connect your radar device with your intercom if it has an input for external audio (e.g. TQ KRT2 has one). This is possible on the Pi Zero with an external USB sound card. I used a simple "3D USB 5.1 Sound card" available for 4 Euro. The sound volume can be controlled via the option "-y 50" or can be modified with the pushbuttons under ->Status-> Net/Opt -> External Volume.
   The following link gives some good hints, which USB sound card can be used and it also shows how to solder it to the Pi Zero, if you do not want an adapter or space is an issue (https://www.raspberrypi-spy.co.uk/2019/06/using-a-usb-audio-device-with-the-raspberry-pi/).
   
   If you are using a Pi3B or Pi4 for the radar-display you can use the builtin audio jack. To enable this, you have to specify "-mx PCM" (select mixer PCM) in stratux_radar.sh along with the option "-y 100" (for sound volume). If you are running the radar-display on the same Pi together with stratux this is currently not supported, since there are software conflicts.
   
### Bluetooth devices
   
   stratux-radar-display will automatically connect the your headset if their bluetooth is switched on. 
   But once you need to do the pairing of a new bluetooth device. 
   
   There are two options for pairing:
   
   **Option 1: Directly on the device via buttons:**
   
   * Change to Status-Mode (long press middle button, to change from Radar-> Timer -> AHRS -> G-Meter -> Compass -> VSI -> Status)
   * Press "scan" (right button). The display now scans 30 secs for new devices. Set your headset as visible and it will be detected (For Bose A20 this is a 5 second press on the Bluetooth-Button until it flashes blue-red)
   * A list of detected devices is shown, press "yes" for the detected device. Sometimes you need to repeat the scan until your headset is detected.
      
   **Option 2: via ssh and bluetoothctl**
   
   * Logon on your radar as user pi:  ssh pi@192.168.x.x
   * change to user root:   sudo -s     (bluetooth is running in system mode!)
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
   - middle button (>1 sec): switch to next mode (radar -> timer -> ahrs -> gmeter -> compass -> vertical speed -> display status -> stratux statux -> flight logs -> radar)
   - left button (>1 sec): start shutdown, press any other button to cancel shutdown
   - after shutdown, display can be reactivated by switching on/off
   - Epaper display: right button > 1 sec does a refresh of the display. Sometimes you may have some fragments on the display (because we are using partial refresh). Pressing the right button does a full refresh.
   
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
 - no special interaction, press middle for next mode

![AHRS](https://github.com/TomBric/stratux-radar-display/blob/main/no-code/images/Epaper-AHRS-Mode.jpg)

### G-Meter mode:
    - press short right to reset min and max values
    - press middle for next mode

![Gmeter](https://github.com/TomBric/stratux-radar-display/blob/main/no-code/images/Epaper-G-Meter-Mode.jpg)

### Compass mode:
    - press middle for next mode

![Compass](https://github.com/TomBric/stratux-radar-display/blob/main/no-code/images/Epaper-CompassMode.jpg)

### Vertical speeed indicator mode:
    - press middle for next mode
    - on epaper: press right to reset max and min values
    
### Display status mode:
    - press middle for next mode
    - press right to start bluetooth-scan
    - press left to show or modify network and other settings, press left again to select Options (external volume, registration, speak distance), press right to modify Network settings (Wifi, passphrase, stratux IP)
    
### Stratux status mode:
    - press middle for next mode
    
### Flight log mode:
    - press middle for next mode
    
# Shell command parameters
```
usage: radar.py [-h] -d DEVICE [-b] [-sd] [-n] [-t] [-a] [-x] [-g] [-o] [-i] [-z] [-w] [-sit] [-chl CHECKLIST] [-stc] [-c CONNECT] [-v VERBOSE] [-r] [-e] [-y EXTSOUND] [-nf] [-nc] [-ci] [-gd] [-gb] [-sim]
                [-mx MIXER] [-modes DISPLAYMODES]

Stratux radar display

optional arguments:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        Display device to use
  -b, --bluetooth       Bluetooth speech warnings on
  -sd, --speakdistance  Speech with distance
  -n, --north           Ground mode: always display north up
  -t, --timer           Start mode is timer
  -a, --ahrs            Start mode is ahrs
  -x, --status          Start mode is status
  -g, --gmeter          Start mode is g-meter
  -o, --compass         Start mode is compass
  -i, --vsi             Start mode is vertical speed indicator
  -z, --strx            Start mode is stratux-status
  -w, --cowarner        Start mode is CO warner
  -sit, --situation     Start mode situation display
  -chl CHECKLIST, --checklist CHECKLIST
                        Checklist file name to use
  -stc, --startchecklist
                        Start mode is checklist
  -c CONNECT, --connect CONNECT
                        Connect to Stratux-IP
  -v VERBOSE, --verbose VERBOSE
                        Debug output level [0-3]
  -r, --registration    Display registration no (epaper only)
  -e, --fullcircle      Display full circle radar (3.7 epaper only)
  -y EXTSOUND, --extsound EXTSOUND
                        Ext sound on with volume [0-100]
  -nf, --noflighttime   Suppress detection and display of flighttime
  -nc, --nocowarner     Suppress activation of co-warner
  -ci, --coindicate     Indicate co warning via GPIO16
  -gd, --grounddistance
                        Activate ground distance sensor
  -gb, --groundbeep     Indicate ground distance via sound
  -sim, --simulation    Simulation mode for testing
  -mx MIXER, --mixer MIXER
                        Mixer name to be used for sound output
  -modes DISPLAYMODES, --displaymodes DISPLAYMODES
                        Select display modes that you want to see R=radar T=timer A=ahrs D=display-status G=g-meter K=compass V=vsi I=flighttime S=stratux-status C=co-sensor M=distance measurement L=checklist
                        Example: -modes RADCM
```


