#!/usr/bin/env python3
"""
Quectel EC25 Auto Port Detection Script
Automatically finds the correct AT command port for EC25 module
"""

import serial
import serial.tools.list_ports
import time
import sys
import os

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'

def test_port(port, baudrate=115200, timeout=0.5):
    """Test if a port responds to AT commands (fast timeout to prevent hanging)"""
    ser = None
    try:
        print(f"{YELLOW}Testing {port} at {baudrate} baud...{RESET}", end=' ', flush=True)

        # Short timeout to prevent hanging on non-responsive ports
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=0.3,
            write_timeout=0.3,  # Prevent write blocking
            rtscts=False,
            dsrdtr=False,
            xonxoff=False
        )

        # Clear any pending data (with timeout protection)
        try:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        except:
            print(f"{RED}✗ (buffer error){RESET}")
            return False, []

        time.sleep(0.1)

        # Test only single AT command for speed
        try:
            ser.write(b"AT\r\n")
        except:
            print(f"{RED}✗ (write timeout){RESET}")
            return False, []

        # Wait max 1 second for response
        start = time.time()
        buf = ""
        while time.time() - start < 1.0:
            try:
                if ser.in_waiting:
                    buf += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    if "OK" in buf:
                        print(f"{GREEN}✓ (AT OK){RESET}")
                        return True, [("AT", "Basic AT", buf)]
            except:
                break
            time.sleep(0.05)

        print(f"{RED}✗ (no response){RESET}")
        return False, []

    except serial.SerialException as e:
        print(f"{RED}✗ (serial error: {e}){RESET}")
        return False, []
    except Exception as e:
        print(f"{RED}✗ (error: {e}){RESET}")
        return False, []
    finally:
        try:
            if ser and ser.is_open:
                ser.close()
        except:
            pass

def find_usb_ports():
    """Find all available USB serial ports"""
    ports = []
    
    # Method 1: Check standard USB serial ports
    for i in range(10):
        for prefix in ['/dev/ttyUSB', '/dev/ttyACM', '/dev/cu.usbserial', '/dev/tty.usbserial']:
            port = f"{prefix}{i}"
            if os.path.exists(port):
                ports.append(port)
    
    # Method 2: Use pyserial's list_ports
    for port in serial.tools.list_ports.comports():
        if port.device not in ports:
            ports.append(port.device)
    
    return sorted(set(ports))

def detect_ec25_info(port, baudrate=115200):
    """Get detailed EC25 module information"""
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(0.5)
        
        info = {}
        commands = {
            'AT+CGMI': 'Manufacturer',
            'AT+CGMM': 'Model',
            'AT+CGMR': 'Firmware',
            'AT+CGSN': 'IMEI',
            'AT+CIMI': 'IMSI',
            'AT+CCID': 'SIM Card ID',
            'AT+CSQ': 'Signal Quality',
            'AT+COPS?': 'Network Operator',
            'AT+CREG?': '2G/3G Registration',
            'AT+CEREG?': 'LTE Registration',
            'AT+QNWINFO': 'Network Info',
            'AT+QENG="servingcell"': 'Serving Cell'
        }
        
        print(f"\n{CYAN}{BOLD}=== Detailed EC25 Information ==={RESET}")
        
        for cmd, desc in commands.items():
            ser.write(f"{cmd}\r\n".encode())
            time.sleep(0.5)
            response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore').strip()
            
            if response and "ERROR" not in response:
                # Clean up response
                lines = response.split('\n')
                clean_response = ' '.join([l.strip() for l in lines if l.strip() and l.strip() != 'OK'])
                
                if clean_response:
                    info[desc] = clean_response
                    print(f"{GREEN}{desc}:{RESET} {clean_response}")
        
        ser.close()
        return info
        
    except Exception as e:
        print(f"{RED}Error getting module info: {e}{RESET}")
        return {}

def main():
    print(f"{CYAN}{BOLD}{'='*60}{RESET}")
    print(f"{CYAN}{BOLD}Quectel EC25 AT Port Auto-Detection Tool{RESET}")
    print(f"{CYAN}{BOLD}{'='*60}{RESET}\n")
    
    # Find all available ports
    print(f"{BLUE}Step 1: Searching for USB serial ports...{RESET}")
    ports = find_usb_ports()
    
    if not ports:
        print(f"{RED}No USB serial ports found!{RESET}")
        print(f"{YELLOW}Please check:{RESET}")
        print("1. EC25 module is connected via USB")
        print("2. USB drivers are installed")
        print("3. You have permission to access serial ports")
        print("   Run: sudo usermod -a -G dialout $USER")
        sys.exit(1)
    
    print(f"{GREEN}Found {len(ports)} port(s): {', '.join(ports)}{RESET}\n")
    
    # Test each port
    print(f"{BLUE}Step 2: Testing each port for AT commands...{RESET}")
    working_ports = []
    partial_ports = []
    
    # Test common baudrates
    baudrates = [115200, 9600, 57600, 38400, 19200]
    
    for port in ports:
        for baudrate in baudrates:
            result, responses = test_port(port, baudrate)
            if result == True:
                working_ports.append((port, baudrate, responses))
                break  # Found working baudrate, skip others
            elif result == "partial":
                partial_ports.append((port, baudrate, responses))
        print()  # Empty line between ports
    
    # Results summary
    print(f"\n{CYAN}{BOLD}{'='*60}{RESET}")
    print(f"{CYAN}{BOLD}Detection Results:{RESET}")
    print(f"{CYAN}{BOLD}{'='*60}{RESET}\n")
    
    if working_ports:
        print(f"{GREEN}{BOLD}✓ Found EC25 AT command port(s):{RESET}")
        for port, baudrate, responses in working_ports:
            print(f"  {GREEN}Port: {port} @ {baudrate} baud{RESET}")
            
            # Get detailed info from the first working port
            if working_ports[0][0] == port:
                detect_ec25_info(port, baudrate)
        
        # Save configuration
        config_file = "ec25_config.txt"
        with open(config_file, 'w') as f:
            f.write(f"# EC25 Configuration (auto-detected)\n")
            f.write(f"PORT={working_ports[0][0]}\n")
            f.write(f"BAUDRATE={working_ports[0][1]}\n")
        
        print(f"\n{GREEN}Configuration saved to {config_file}{RESET}")
        print(f"\n{CYAN}{BOLD}To use with LTE collector:{RESET}")
        print(f"python3 lte_remote_collector_en.py --serial-port {working_ports[0][0]} --baudrate {working_ports[0][1]}")
        
    elif partial_ports:
        print(f"{YELLOW}⚠ Found ports with partial responses:{RESET}")
        for port, baudrate, responses in partial_ports:
            print(f"  {YELLOW}Port: {port} @ {baudrate} baud{RESET}")
            for cmd, desc, resp in responses[:3]:  # Show first 3 responses
                print(f"    {desc}: {resp[:50]}...")
    else:
        print(f"{RED}✗ No EC25 module detected on any port!{RESET}")
        print(f"\n{YELLOW}Troubleshooting steps:{RESET}")
        print("1. Check USB connection")
        print("2. Check module power (LED status)")
        print("3. Try: sudo systemctl stop ModemManager")
        print("4. Try: sudo chmod 666 /dev/ttyUSB*")
        print("5. Check dmesg for USB errors: dmesg | grep -i usb")
        
        # Additional diagnostics
        print(f"\n{YELLOW}USB device information:{RESET}")
        os.system("lsusb | grep -i 'quectel\\|2c7c\\|05c6'")
        
        print(f"\n{YELLOW}Kernel messages:{RESET}")
        os.system("dmesg | grep -i 'ttyUSB\\|quectel' | tail -5")

if __name__ == "__main__":
    main()