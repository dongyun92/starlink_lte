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

# First check if EC25 config exists from auto-detection
if [ -f "ec25_config.txt" ]; then
    echo -e "${GREEN}✓ Found EC25 configuration file${NC}"
    SERIAL_PORT=$(grep "^PORT=" ec25_config.txt | cut -d'=' -f2)
    BAUDRATE=$(grep "^BAUDRATE=" ec25_config.txt | cut -d'=' -f2)
    echo -e "${GREEN}✓ Using detected port: $SERIAL_PORT @ $BAUDRATE baud${NC}"
else
    # Try auto-detection with find_ec25_port.py
    echo -e "${YELLOW}Running EC25 auto-detection...${NC}"
    if [ -f "find_ec25_port.py" ]; then
        python3 find_ec25_port.py
        if [ -f "ec25_config.txt" ]; then
            SERIAL_PORT=$(grep "^PORT=" ec25_config.txt | cut -d'=' -f2)
            BAUDRATE=$(grep "^BAUDRATE=" ec25_config.txt | cut -d'=' -f2)
            echo -e "${GREEN}✓ Auto-detected port: $SERIAL_PORT @ $BAUDRATE baud${NC}"
        fi
    fi
    
    # Fallback to manual search
    if [ -z "$SERIAL_PORT" ]; then
        echo -e "${YELLOW}Manual port search...${NC}"
        # Prioritize /dev/ttyUSB2 for EC25
        for port in /dev/ttyUSB2 /dev/ttyUSB0 /dev/ttyUSB1 /dev/ttyUSB3 /dev/ttyACM0 /dev/ttyACM1; do
            if [ -e "$port" ]; then
                echo -e "${GREEN}✓ Port found: $port${NC}"
                SERIAL_PORT=$port
                BAUDRATE=115200
                break
            fi
        done
    fi
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
python3 test_at_commands.py --port $SERIAL_PORT --baudrate $BAUDRATE

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
        --interval 5
        
else
    echo -e "${YELLOW}Cancelled${NC}"
fi