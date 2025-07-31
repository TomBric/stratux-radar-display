#!/bin/bash

# Test script for Stratux Radar Buttons API
# Usage: ./api_test.sh [host[:port]]
#   host:  The hostname or IP address of the Stratux Radar Display (default: localhost)
#   port:  The port number (default: 5000)
#
# Examples:
#   ./api_test.sh                     # Uses default localhost:5000
#   ./api_test.sh 192.168.1.100       # Connects to 192.168.1.100:5000
#   ./api_test.sh 192.168.1.100:8080  # Connects to 192.168.1.100:8080
#
# Start Stratux display with options:
#   python3 radar.py -d <display> -api -v 1
# or for full functionality:
#   python3 radar.py -d <display> -api -v1 -gd -gb -y 50
# or in dark mode:
#   python3 radar.py -d <display> -api -v1 -gd -gb -y 50 --dark

# Default values
DEFAULT_HOST="localhost"
DEFAULT_PORT="5000"

# Parse command line arguments
if [ $# -eq 0 ]; then
    # No arguments, use default host and port
    HOST_PORT="$DEFAULT_HOST:$DEFAULT_PORT"
elif [[ "$1" == *""* ]]; then
    # Argument contains port number (contains a colon)
    HOST_PORT="$1"
else
    # Only host provided, use default port
    HOST_PORT="$1:$DEFAULT_PORT"
fi

# Ensure the URL has the correct format
if [[ "$HOST_PORT" != http* ]]; then
    HOST_PORT="http://$HOST_PORT"
fi

# Set the base URL for API requests
BASE_URL="${HOST_PORT}/api"

# Extract just the host:port part for display
DISPLAY_HOST_PORT=${HOST_PORT#http://}
DISPLAY_HOST_PORT=${DISPLAY_HOST_PORT#https://}

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to test a button press
test_button() {
    local data_param=$1
    local output=$2
    local sleep=$3

    # Display output if second parameter is provided
    if [ -n "$output" ]; then
        echo -n "$output "
    fi

    # Send the request
    response=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
              -H "Content-Type: application/x-www-form-urlencoded" \
              -d "$data_param" \
              "$BASE_URL" 2>&1)

    # Check if the request was successful
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        echo "Response: $response"
    fi
    if [ -n "$sleep" ]; then
        sleep $sleep
    else
        sleep 1
    fi

}

# Test all button combinations
echo "Testing Radar User Interface at $DISPLAY_HOST_PORT"
echo "Base API URL: $BASE_URL"
echo ""

echo Radar screen distance
for i in {1..7}; do
  test_button "left_short=Left Short"
done


echo Radar screen height
for i in {1..5}; do
  test_button "right_short=Right Short"
done

echo Sound on/off
test_button "middle_short=Middle Short"
test_button "middle_short=Middle Short"

echo shutdown + cancel
test_button "left_long=Left Long"
test_button "left_short=Left Short"

echo refresh
test_button "right_long=Right Long" "Refresh" 5

echo "------------------------------------"
echo "Timer"
test_button "middle_long=Middle Long"
test_button "right_short=Right Short"
test_button "right_short=Right Short"
test_button "right_short=Right Short"
test_button "left_short=Left Short"
test_button "middle_short=Middle Short"
test_button "left_short=Left Short"
test_button "left_short=Left Short"
test_button "right_short=Right Short"
test_button "right_short=Right Short"
test_button "middle_short=Middle Short"
test_button "right_short=Right Short"
test_button "right_short=Right Short"
test_button "left_short=Left Short"
sleep 1

echo "------------------------------------"
echo "AHRS"
test_button "middle_long=Middle Long" "AHRS" 2
sleep 2
test_button "right_short=Right Short" "Zero" 4
test_button "left_short=Left Short" "Level" 4

echo "------------------------------------"
echo "G-Force"
test_button "middle_long=Middle Long"
test_button "right_short=Right Short"

echo "------------------------------------"
echo "Compass"
test_button "middle_long=Middle Long"
test_button "right_long=Right Long" "Refresh" 4

echo "------------------------------------"
echo "Vertical Speed"
test_button "middle_long=Middle Long" "VSI" 3
test_button "right_short=Right Short" "Reset"

echo "------------------------------------"
echo "Flight Logs"
test_button "middle_long=Middle Long" "Display Logs" 3
test_button "right_short=Right Short" "Clear" 3

echo "------------------------------------"
echo "GPS Distance"
test_button "middle_long=Middle Long" "Display Dist" 3
test_button "right_short=Right Short"
test_button "left_short=Left Short"
test_button "middle_short=Middle Short"
test_button "middle_short=Middle Short"
test_button "left_short=Left Short"
test_button "left_short=Left Short"
test_button "middle_short=Middle Short"

echo "------------------------------------"
echo "Display Status"
test_button "middle_long=Middle Long" "Status" 3
test_button "left_short=Left Short" "Opt/Net"
test_button "left_short=Left Short" "Opt"
test_button "left_short=Left Short" "Show reg YES"
test_button "Right_short=Right Short" "Speak Dist NO"
test_button "Right_short=Right Short" "Chg Network"
test_button "left_short=Left Short" "+"
test_button "middle_short=Middle Short" "Next"
test_button "middle_short=Middle Short" "Next"
test_button "middle_long=Middle Long" "Fin" 3
test_button "middle_long=Middle Long" "Enter Passwd" 3
echo "Enter IP"
for i in {1..5}; do
  test_button "middle_short=Middle Short"
done
test_button "middle_long=Middle Long" "Fin" 3
test_button "Right_short=Right Short" "Confirm No" 3
test_button "middle_short=Middle Short" "Cont"

echo "------------------------------------"
echo "Stratux Status"
test_button "middle_short=Middle Short"
test_button "left_short=Left Short" "+10"
test_button "right_short=Right Short" "-10"

echo "------------------------------------"
echo "Checklist"
test_button "middle_short=Middle Short"
for i in {1..10}; do
  test_button "right_short=Right Short"
done
test_button "middle_short=Middle Short"
test_button "middle_short=Middle Short"
test_button "left_short=Left Short"
test_button "left_short=Left Short"
echo "------------------------------------"
test_button "middle_long=Middle Long" "Back To Radar" 5
echo "Testing complete!"

# Test the API form (GET request)
echo -n "Testing API form - GET request ... "
http_code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL")
if [ "$http_code" -eq 200 ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED HTTP $http_code ${NC}"
fi

echo "You can also test the web interface by opening http://$HOST/api in your browser"