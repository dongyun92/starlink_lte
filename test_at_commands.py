#!/usr/bin/env python3
"""
Quectel EC25/EC21 LTE Module AT Command Test Script
Tests AT commands with actual hardware connection
"""

import serial
import time
import sys
import argparse

def test_at_command(ser, command, wait_time=1, description=""):
    """Test AT command and display response"""
    print(f"\n{'='*60}")
    if description:
        print(f"Test: {description}")
    print(f"Command: {command}")
    print("-" * 40)
    
    try:
        # Send command
        ser.write(f"{command}\r\n".encode())
        time.sleep(wait_time)
        
        # Read response
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        
        if response:
            print(f"Response:\n{response}")
            return True
        else:
            print("No response")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='LTE Module AT Command Tester')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
    parser.add_argument('--baudrate', type=int, default=115200, help='Baud rate')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Quectel EC25/EC21 LTE Module Test")
    print("=" * 60)
    print(f"Port: {args.port}")
    print(f"Baud rate: {args.baudrate}")
    
    try:
        # Connect to serial port
        ser = serial.Serial(
            port=args.port,
            baudrate=args.baudrate,
            timeout=1,
            rtscts=True,
            dsrdtr=True
        )
        
        print(f"\n✅ Serial port connected successfully: {args.port}")
        
        # Basic AT command tests
        tests = [
            ("AT", 1, "Basic communication test"),
            ("ATI", 1, "Module information"),
            ("AT+CGMI", 1, "Manufacturer information"),
            ("AT+CGMM", 1, "Model name"),
            ("AT+CGSN", 1, "IMEI number"),
            ("AT+CSQ", 1, "Signal strength (RSSI, BER)"),
            ("AT+CREG?", 1, "2G/3G network registration status"),
            ("AT+CEREG?", 1, "LTE network registration status"),
            ("AT+COPS?", 1, "Current network operator"),
            ("AT+QNWINFO", 1, "Network info (type, band, channel)"),
            ("AT+CIMI", 1, "IMSI (SIM card information)"),
            ("AT+CCID", 1, "SIM card ID"),
            ("AT+QGDCNT?", 1, "Data usage (RX/TX)"),
            ("AT+CGPADDR", 1, "IP address"),
            ("AT+QENG=\"servingcell\"", 2, "Serving cell details"),
            ("AT+QCSQ", 1, "Extended signal quality info"),
            ("AT+QRSRP", 1, "RSRP (Reference Signal Received Power)"),
            ("AT+QRSRQ", 1, "RSRQ (Reference Signal Received Quality)"),
            ("AT+QSINR", 1, "SINR (Signal to Interference plus Noise Ratio)"),
        ]
        
        success_count = 0
        fail_count = 0
        
        for cmd, wait, desc in tests:
            if test_at_command(ser, cmd, wait, desc):
                success_count += 1
            else:
                fail_count += 1
            time.sleep(0.5)
        
        # Result summary
        print("\n" + "=" * 60)
        print("Test Result Summary")
        print("=" * 60)
        print(f"✅ Success: {success_count}")
        print(f"❌ Failed: {fail_count}")
        
        if success_count > 0:
            print("\n🎉 LTE module is working properly!")
            print("Real data collection is available.")
        else:
            print("\n⚠️ No response from LTE module")
            print("Please check the following:")
            print("1. Module power connection status")
            print("2. Serial port settings (port name, baud rate)")
            print("3. USB cable connection status")
            print("4. Module driver installation")
        
        # Close serial port
        ser.close()
        
    except serial.SerialException as e:
        print(f"\n❌ Serial port connection failed: {e}")
        print("\nSolutions:")
        print("1. Check correct port name:")
        print("   - Linux: /dev/ttyUSB0, /dev/ttyUSB1, ...")
        print("   - Mac: /dev/cu.usbserial-*, /dev/tty.usbserial-*")
        print("   - Windows: COM3, COM4, ...")
        print("2. Check port permissions (Linux/Mac):")
        print("   sudo chmod 666 /dev/ttyUSB0")
        print("3. Check if another program is using the port")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()