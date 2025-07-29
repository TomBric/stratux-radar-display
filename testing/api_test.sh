#!/bin/bash

# Test script for Stratux Radar Buttons API
# Usage: ./api_test.sh [host:port]
# Tests all screen functions
# start Stratux display with options
# python3 radar.py -d <display> -api -v 1
# or for full functionality
# python3 radar.py -d <display> -api -v1 -gd -gb -y 50
# or in dark mode
# python3 radar.py -d <display> -api -v1 -gd -gb -y 50 --dark

# Default host and port
HOST=${1:-"localhost:5000"}
BASE_URL="http://$HOST/api"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to test a button press
test_button() {
    local data_param=$1

    # Send the request
    response=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
              -H "Content-Type: application/x-www-form-urlencoded" \
              -d "$data_param" \
              "$BASE_URL" 2>&1)

    # Check if the request was successful
    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        echo "Response: $response"
        return 1
    fi
}

# Test all button combinations
echo "Testing Radar User Interface at $BASE_URL"
echo ""

echo Radar screen distance
for i in {1..7}; do
  test_button "left_short=Left Short"
  sleep 1  # Small delay between tests
done


echo Radar screen height
for i in {1..5}; do
  test_button "right_short=Right Short"
  sleep 1
done

echo Sound on/off
test_button "middle_short=Middle Short"
sleep 1
test_button "middle_short=Middle Short"
sleep 1

echo shutdown + cancel
test_button "left_long=Left Long"
sleep 1
test_button "left_short=Left Short"
sleep 1

echo refresh
test_button "right_long=Right Long"
sleep 5

echo "------------------------------------"
echo "Timer"
test_button "middle_long=Middle Long"
sleep 1
test_button "right_short=Right Short"
sleep 1
test_button "right_short=Right Short"
sleep 1
test_button "right_short=Right Short"
sleep 1
test_button "left_short=Left Short"
sleep 1
test_button "middle_short=Middle Short"
sleep 1
test_button "left_short=Left Short"
sleep 1
test_button "left_short=Left Short"
sleep 1
test_button "right_short=Right Short"
sleep 1
test_button "right_short=Right Short"
sleep 1
test_button "middle_short=Middle Short"
sleep 1
test_button "right_short=Right Short"
sleep 3
test_button "right_short=Right Short"
sleep 3
test_button "left_short=Left Short"
sleep 1

echo "------------------------------------"
echo "AHRS"
test_button "middle_long=Middle Long"
sleep 1
test_button "right_short=Right Short"
sleep 4
test_button "left_short=Left Short"
sleep 1

echo "------------------------------------"
echo "G-Force"
test_button "middle_long=Middle Long"
sleep 1
test_button "right_short=Right Short"
sleep 1

echo "------------------------------------"
echo "Compass"
test_button "middle_long=Middle Long"
sleep 4
test_button "right_long=Right Long"
sleep 4

echo "------------------------------------"
echo "Vertical Speed"
test_button "middle_long=Middle Long"
sleep 3
test_button "right_short=Right Short"
sleep 1

echo "------------------------------------"
echo "Flight Logs"
test_button "middle_long=Middle Long"
sleep 3
test_button "right_short=Right Short"
sleep 1

echo "------------------------------------"
echo "GPS Distance"
test_button "middle_long=Middle Long"
sleep 3
test_button "right_short=Right Short"
sleep 1
test_button "left_short=Left Short"
sleep 1
test_button "middle_short=Middle Short"
sleep 1
test_button "middle_short=Middle Short"
sleep 1
test_button "left_short=Left Short"
sleep 1
test_button "left_short=Left Short"
sleep 1
test_button "middle_short=Middle Short"
sleep 1

echo "------------------------------------"
echo "Display Status"
test_button "middle_long=Middle Long"
sleep 3
echo "Options"
test_button "left_short=Left Short"
sleep 1
test_button "left_short=Left Short"
sleep 1
test_button "Right_short=Right Short"
sleep 1
echo "Change Network"
test_button "Right_short=Right Short"
sleep 1
echo "Change Network"
test_button "left_short=Left Short"
sleep 3
test_button "middle_long=Middle Long"
sleep 3
test_button "middle_long=Middle Long"
sleep 3
for i in {1..5}; do
  test_button "middle_short=Middle Short"
  sleep 1
done
test_button "middle_long=Middle Long"
sleep 3
test_button "Right_short=Right Short"
sleep 1
test_button "middle_short=Middle Short"
sleep 1

echo "------------------------------------"
echo "Stratux Status"
test_button "middle_short=Middle Short"
sleep 1
test_button "left_short=Left Short"
sleep 1
test_button "right_short=Right Short"
sleep 1

echo "------------------------------------"
echo "Checklist"
test_button "middle_short=Middle Short"
sleep 1
for i in {1..10}; do
  test_button "right_short=Right Short"
  sleep 1
done
test_button "middle_short=Middle Short"
sleep 1
test_button "middle_short=Middle Short"
sleep 1
test_button "left_short=Left Short"
sleep 1
test_button "left_short=Left Short"
sleep 1
echo "------------------------------------"
test_button "middle_long=Middle Long"
sleep 3
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