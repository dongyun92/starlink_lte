#!/bin/bash

echo "========================================="
echo "LTE Real Data Collection Start Script"
echo "========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Terminate existing processes
echo -e "\n${YELLOW}Terminating existing processes...${NC}"
pkill -f "lte_remote_collector"
sleep 2

# Search for serial port
echo -e "\n${YELLOW}Searching for LTE module...${NC}"

# Check Linux serial ports
SERIAL_PORT=""
for port in /dev/ttyUSB0 /dev/ttyUSB1 /dev/ttyUSB2 /dev/ttyACM0 /dev/ttyACM1; do
    if [ -e "$port" ]; then
        echo -e "${GREEN}✓ Port found: $port${NC}"
        SERIAL_PORT=$port
        break
    fi
done

# Check Mac serial ports
if [ -z "$SERIAL_PORT" ]; then
    for port in /dev/cu.usbserial* /dev/tty.usbserial* /dev/cu.usbmodem* /dev/tty.usbmodem*; do
        if [ -e "$port" ]; then
            echo -e "${GREEN}✓ Port found: $port${NC}"
            SERIAL_PORT=$port
            break
        fi
    done
fi

# If port not found
if [ -z "$SERIAL_PORT" ]; then
    echo -e "${RED}✗ LTE module not found${NC}"
    echo -e "${YELLOW}Running in Mock mode...${NC}"
    SERIAL_PORT="/dev/ttyUSB0"  # Use default (Mock mode auto-enabled)
else
    # Set port permissions (Linux/Mac)
    echo -e "\n${YELLOW}Setting port permissions...${NC}"
    sudo chmod 666 $SERIAL_PORT 2>/dev/null || true
fi

# AT command test
echo -e "\n${YELLOW}Running AT command test...${NC}"
python3 test_at_commands.py --port $SERIAL_PORT --baudrate 115200

# User confirmation
echo -e "\n${YELLOW}Start LTE data collection? (y/n)${NC}"
read -r response

if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
    # Create data directory
    mkdir -p lte-collector-data
    
    # Start LTE collector
    echo -e "\n${GREEN}Starting LTE data collection...${NC}"
    echo "Port: $SERIAL_PORT"
    echo "Control port: 8897"
    echo "Data directory: ./lte-collector-data/"
    echo ""
    
    python3 lte_remote_collector_en.py \
        --data-dir ./lte-collector-data \
        --control-port 8897 \
        --serial-port $SERIAL_PORT \
        --baudrate 115200 \
        --interval 5
        
else
    echo -e "${YELLOW}Cancelled${NC}"
fi