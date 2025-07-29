#!/bin/bash

# Test script for Stratux Radar Buttons API
# Usage: ./test_radar_buttons.sh [host:port]
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
  "middle_long=Middle Long"
    local button_name=$1
    local button_desc=$2
    local data_param=$3

    echo -n "Testing $button_desc... "

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
echo "-----------------------------------------"

# radar screen - distance
for i in {1..6}; do
  test_button "left_short" "Left Short Press" "left_short=Left+Short"
  sleep 1  # Small delay between tests
done

# radar-screen - height
for i in {1..5}; do
  test_button "right_short" "Right Short Press" "right_short=Right+Short"
  sleep 1
done

# sound on off
test_button "middle_short" "Middle Short Press" "middle_short=Middle+Short"
sleep 1
test_button "middle_short" "Middle Short Press" "middle_short=Middle+Short"
sleep 1

# shutdown + cancel
test_button "left_long" "Left Long Press" "left_long=Left+Long"
sleep 1
test_button "left_short" "Left Short Press" "left_short=Left+Short"
echo "------------------------------------"
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