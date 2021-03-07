rem simple windows batch skript for remote update
rem usage: remote_update <update-zip-file> <stratux-radar-ip>
rem zip-file has to be downloaded from github (download zip)
rem example: remote_update stratux-radar-display-main.zip 192.168.10.10 MyPASSWORD

scp %1 pi@%2:/home/pi/%1
ssh pi@%2 "unzip /home/pi/%1; /bin/bash stratux-radar-display-main/image/update_radar.sh"