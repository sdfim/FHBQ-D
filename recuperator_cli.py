#!/usr/bin/env python3

# Required libraries for serial communication, encoding, timing, and system interaction
import binascii
import codecs
import time
import serial
import sys
import csv

# --- Configuration and Initialization ---

# Global constants for serial connection
S_PORT = '/dev/ttyUSB0'
B_RATE = 9600
MAX_SEND = 10 # Maximum number of attempts to send a command

# Debug flags (use True/False)
PRINT_CHECKING = False # Detailed comparison of packets and attempt counter
PRINT_PREINFO = False  # Current status before sending a command
PRINT_UNIT = False     # Device status packet
PRINT_PAST = False     # Subsequent raw packets

# ANSI color codes for styled console output
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Serial port initialization.
try:
    # Setting a short timeout for read operations (0.5 seconds)
    ser = serial.Serial(port=S_PORT, baudrate=B_RATE, timeout=0.5)
except serial.SerialException as e:
    # Using .format()
    print(bcolors.FAIL + "ERROR: Failed to open serial port {}. ({})".format(S_PORT, e) + bcolors.ENDC)
    ser = None # Set to None if initialization failed

# --- Helper functions: Conversion and checksum ---

def get_dic(data):
    """Converts a bytes object into a list of 2-character hexadecimal strings."""
    return ['{:02x}'.format(el) for el in data]

def HexToByte(hexStr):
    """Converts a hexadecimal string into a bytes object."""
    # Removes spaces and uses a more robust decoding method via codecs
    hexStr = ''.join(hexStr.split(" "))
    return codecs.decode(hexStr, 'hex_codec')

def get_checksum(packet_bytes):
    """Calculates the XOR checksum for a given sequence of bytes."""
    checksum = 0
    # Starting with Python 3, iterating over bytes yields int, which is ideal for XOR
    for el in packet_bytes:
        checksum ^= el
    checksum_hex = '{:02x}'.format(checksum)

    if PRINT_CHECKING:
        # Using .format()
        print('checksum = {}'.format(checksum_hex))

    return checksum_hex

# --- Serial communication functions ---

def get_position():
    """Reads bytes until the synchronization header (\x7e\x7e\xa0\x00) is found."""
    if PRINT_CHECKING:
        print('get_position run')
    # Reset input buffer before attempting synchronization
    if ser: ser.reset_input_buffer()
    while True:
        # ser.read(1) with a timeout of 0.5s
        data = ser.read(1)
        if not data:
            # Stop if timeout occurred (no data)
            if PRINT_CHECKING: print("Timeout while getting position.")
            return False
        if data == b'\x7e':
            data += ser.read(3)
            # This header signals a device status packet
            if data == b'\x7e\x7e\xa0\x00':
                ser.read(13) # Consume the rest of the status packet
                break
    return True

def read_serial(q):
    """Reads a complete packet from the serial port based on the expected header type (q)."""
    if ser is None: return None

    # We know packets are short, so a timeout can be set.
    # Headers (4 bytes) + Body (13 bytes) + Checksum (1 byte) = 18 bytes

    while True:
        # Clear the buffer to avoid reading old or incomplete data
        ser.reset_input_buffer()

        data = ser.read(1)
        if not data: raise serial.SerialTimeoutException("Timeout reading first byte.")

        if data == b'\x7e':
            data += ser.read(1)
            if data == b'\x7e\x7e':
                if q == 'hex':
                    data += ser.read(15)
                    return data
                else:
                    data += ser.read(2)

                    # Header 'revise': ACK/status packet from the device
                    if (q == 'revise' and data == b'\x7e\x7e\xc0\xff'):
                        data += ser.read(13)
                        return data
                    # Header 'start': Command initiation packet
                    if (q == 'start' and data == b'\x7e\x7e\x00\xa0'):
                        data += ser.read(13)
                        return data
                    # Header 'unit': Device status packet (used in get_position)
                    if (q == 'unit' and data == b'\x7e\x7e\xa0\x00'):
                        data += ser.read(13)
                        return data
            # If incomplete header, the loop continues
        # If the first byte is not \x7e, the loop continues

def checking_sended(send, rev):
    """Checks if the device acknowledged the command by reading the 'revise' packet (ACK)."""

    if PRINT_CHECKING:
        print("!!! rev (Original status) = ", rev)

    try:
        # Read the expected ACK/revise packet
        check = get_dic(read_serial('revise'))
    except Exception as e:
        # Using .format()
        print(bcolors.FAIL + "Error reading ACK: {} ".format(e) + bcolors.ENDC)
        return 'ERROR' # Error reading ACK

    # Remove the checksum from the received packet
    del check[16]

    # Compare packets
    sum_check = sum(1 for j in range(4, 16) if check[j] == send[j])

    ch = 'OK_SENT' if sum_check == 12 else 'ERROR'

    if PRINT_PREINFO:
        color = bcolors.OKGREEN if ch == 'OK_SENT' else bcolors.FAIL
        print(color + bcolors.BOLD + ch + bcolors.ENDC)

    # Logic for detailed packet comparison
    if PRINT_CHECKING:
        # Indices where the received ACK differs from the sent command (send)
        diff = [j for j in range(4, 16) if send[j] != check[j]]

        print(bcolors.WARNING + '                                  bp sp      mode     ' + bcolors.ENDC)
        str_sended = ''
        str_checking = ''

        # Build strings with color highlighting for differences
        for j in range(2, 16):
            if j in diff:
                str_sended += ' ' + bcolors.WARNING + bcolors.BOLD + str(send[j]) + bcolors.ENDC
                str_checking += ' ' + bcolors.FAIL + bcolors.BOLD + str(check[j]) + bcolors.ENDC
            else:
                str_sended += ' ' + str(send[j])
                str_checking += ' ' + str(check[j])

        # Using .format()
        print('sended:  {}'.format(str_sended))
        print('checking:{}'.format(str_checking))

        if PRINT_PAST:
            i = 1
            while i <= 3:
                # Using .format()
                print('       {}'.format(" ".join(get_dic(read_serial("hex")))))
                i += 1

    return ch

def read_status():
    """Reads the current operating status of the device and returns a dictionary of settings."""
    start_time_read = time.time()

    while True:
        try:
            rx = get_dic(read_serial('revise'))
            break
        except Exception:
            # If reading failed, attempt to synchronize
            if not get_position():
                 return {'mode': 'unknown', 'speed': 'unknown', 'bypass': 'unknown', 'error': 'TIMEOUT'}

    status = {}

    # Check for off state (byte 9)
    if rx[9] in ('0a', '2a', '4a'):
        status['mode'] = 'off'
        status['speed'] = 0
        status['bypass'] = 'n/a'
        return status

    # Decode Bypass mode (byte 9)
    if rx[9] == '8a': status['bypass'] = 'auto'
    elif rx[9] == 'aa': status['bypass'] = 'on'
    elif rx[9] == 'ca': status['bypass'] = 'off'
    else: status['bypass'] = 'unknown'

    # Decode operating mode (byte 13) and speed (byte 10)
    mode_map = {
        # Normal modes (byte 13 == '20')
        ('20', '0c'): ('normal', 1), ('20', '12'): ('normal', 2), ('20', '21'): ('normal', 3),
        ('20', '4a'): ('normal exhaust', 1), ('20', '51'): ('normal exhaust', 3),
        ('20', '94'): ('normal supply', 1), ('20', 'a2'): ('normal supply', 3),
        # Energy-saving mode (Save Mode) (byte 13 == '10')
        ('10', '0c'): ('save', 1), ('10', '12'): ('save', 2), ('10', '21'): ('save', 3),
        ('10', '4a'): ('save exhaust', 1), ('10', '51'): ('save exhaust', 3),
        ('10', '94'): ('save supply', 1), ('10', 'a2'): ('save supply', 3),
    }

    mode_key = (rx[13], rx[10])
    mode_info = mode_map.get(mode_key, ('unknown', 'unknown'))

    status['mode'] = mode_info[0]
    status['speed'] = mode_info[1]

    if PRINT_CHECKING:
        # Using .format()
        print("Status read time: {:.6f} seconds".format(time.time() - start_time_read))

    return status

# Main function to execute a command
def run_com(cm, ret):
    """
    Executes a command (cm) on the recuperator.
    cm is a list: [mode, speed, bypass] or [hex_command, hex_string]
    """
    start_time_run = time.time()

    # 1. Capture the current status packet (rev) to use as a baseline
    try:
        rev = get_dic(read_serial('revise'))
    except Exception:
        # Attempt to synchronize if reading status failed
        if not get_position():
            return {'answer': 'ERROR', 'status': {'mode': 'sync_fail', 'speed': 0}}
        try:
             rev = get_dic(read_serial('revise'))
        except Exception as e:
             return {'answer': 'ERROR', 'status': {'mode': 'read_fail', 'speed': 0, 'detail': str(e)}}

    # 2. Prepare the command (rx) based on the current status (rev)
    rx = list(rev)
    del rx[16] # Remove checksum from current status

    # Set the command packet header: '00', 'a0'
    rx[2] = '00'
    rx[3] = 'a0'

    # --- Command logic application ---
    if cm[0] == 'h':
        # Raw Hex Command
        com_hex_str = cm[1]
        com_bytes = HexToByte(com_hex_str)

        if PRINT_PREINFO:
            print(bcolors.WARNING + 'Sending raw Hex:' + bcolors.ENDC)
            print ('send:  ' + ' '.join(get_dic(com_bytes)))

        ser.write(com_bytes)
        time.sleep(0.1) # Delay for raw command

        # For raw commands, do not perform ACK check and retry as in the original
        if ret == 'ret':
            return {'answer': 'SENT', 'status': read_status()}
        else:
            if PRINT_PREINFO:
                print ('Response:')
                for _ in range(3):
                    # Using .format()
                    print('       {}'.format(" ".join(get_dic(read_serial("hex")))))
            sys.exit()

    elif cm[0] == 'off':
        # Logic for turning off (changing byte 9)
        if rx[9] == '8a': rx[9] = '0a'
        elif rx[9] == 'aa': rx[9] = '2a'
        elif rx[9] == 'ca': rx[9] = '4a'

    elif cm[0] == 'rhoff':
        # Logic for disabling humidity control (byte 11)
        if rx[9] in ('8a', 'aa', 'ca'): rx[11] = '40'
        if PRINT_PREINFO: print ('Using rhoff')

    elif cm[0] == 'rhon':
        # Logic for enabling humidity control (byte 11)
        if rx[9] in ('8a', 'aa', 'ca'): rx[11] = 'd0'
        if PRINT_PREINFO: print ('Using rhon')

    else:
        # Standard three-part command logic

        # Set Bypass mode (byte 9)
        if cm[2] == 'auto': rx[9] = '8a'
        elif cm[2] == 'on': rx[9] = 'aa'
        elif cm[2] == 'off': rx[9] = 'ca'

        # Mode and speed mapping
        mode_speed_map = {
            # Normal modes (rx[13] = '20')
            ('n', '1'): ('20', '0c'), ('n', '2'): ('20', '12'), ('n', '3'): ('20', '21'),
            ('ne', '1'): ('20', '4a'), ('ne', '3'): ('20', '51'),
            ('ns', '1'): ('20', '94'), ('ns', '3'): ('20', 'a2'),
            # Energy-saving modes (Save Mode) (rx[13] = '10')
            ('s', '1'): ('10', '0c'), ('s', '2'): ('10', '12'), ('s', '3'): ('10', '21'),
            ('se', '1'): ('10', '4a'), ('se', '3'): ('10', '51'),
            ('ss', '1'): ('10', '94'), ('ss', '3'): ('10', 'a2'),
        }

        mode_key = (cm[0], cm[1])
        mode_hex, speed_hex = mode_speed_map.get(mode_key, (None, None))

        if mode_hex and speed_hex:
            rx[13] = mode_hex
            rx[10] = speed_hex
        else:
            if ret == 'ret': return "ERROR: Invalid mode/speed combination."
            else:
                # Using concatenation
                sys.exit(bcolors.FAIL + "ERROR: Invalid mode/speed combination." + bcolors.ENDC)

    # 3. Finalize and send the command

    # Calculate the checksum for the packet body (starting from byte 2)
    packet_body = HexToByte(''.join(rx[2:]))
    checksum_hex = get_checksum(packet_body)

    # Full command string: Header (7e7e) + Body + Checksum
    com = ''.join(rx) + checksum_hex

    answer = ''
    i = 1

    # Retry loop until successful confirmation is received or max attempts reached
    while answer != "OK_SENT":

        # Get 'start' packet before sending command for synchronization
        try:
            get_dic(read_serial('start'))
        except Exception as e:
            if PRINT_CHECKING: print("Error reading start packet: {}".format(e))
            if not get_position(): # Retry synchronization
                 answer = "ERROR"
                 break # Exit loop if synchronization fails

        if i > MAX_SEND:
            answer = "ERROR"
            break

        # Send the command
        ser.write(HexToByte(com))

        # *** STABILIZING DELAY ***
        # Gives the recuperator 100ms to process the command and send ACK
        time.sleep(0.1)

        answer = checking_sended(rx, rev) # Check ACK
        i += 1

    # 4. Display results and return/exit

    if PRINT_CHECKING:
        # Using .format()
        print("{} attempts to send. Total time: {:.6f} seconds".format(i-1, time.time() - start_time_run))

    final_status = read_status()

    if ret == 'ret':
        # Return status dictionary for use as a library function
        return {'answer': answer, 'status': final_status}
    else:
        # CLI exit logic
        if PRINT_PREINFO:
            # Using .format()
            status_str = "mode: {}; speed: {}; bypass: {};".format(final_status.get('mode'), final_status.get('speed'), final_status.get('bypass'))
            # Using concatenation
            print(bcolors.WARNING + "Current status: " + bcolors.ENDC + bcolors.OKBLUE + bcolors.BOLD + status_str + bcolors.ENDC)

        if answer != "OK_SENT":
            # Using concatenation
            print(bcolors.FAIL + 'ERROR' + bcolors.ENDC)
        else:
            # Using concatenation
            print(bcolors.OKGREEN + 'DONE' + bcolors.ENDC)

        if ser and ser.is_open:
            ser.close()
        sys.exit()

# --- Public library interface and validation ---

# List of valid command combinations
COM_VALID=[
"n1auto", "n2auto", "n3auto", "n1on", "n2on", "n3on", "n1off", "n2off", "n3off",
"ne1auto", "ne3auto", "ne1on", "ne3on", "ne1off", "ne3off",
"ns1auto", "ns3auto", "ns1on", "ns3on", "ns1off", "ns3off",
"s1auto", "s2auto", "s3auto", "s1on", "s2on", "s3on", "s1off", "s2off", "s3off",
"se1auto", "se3auto", "se1on", "se3on", "se1off", "se3off",
"ss1auto", "ss3auto", "ss1on", "ss3on", "ss1off", "ss3off"]

# !!! PUBLIC FUNCTION FOR BACKWARD COMPATIBILITY !!!
def fhbq_start(a='status', b=None, c=None):
    """
    Public interface for controlling the recuperator.
    """
    if ser is None:
        return {'answer': 'ERROR', 'mode': 'SERIAL_INIT_FAILED', 'speed': 0}

    if b is None and c is None:
        # Single-word commands: status, off, rhoff, rhon
        if a == 'status':
            return read_status()
        if a in ('off', 'rhoff', 'rhon'):
            return run_com([a, ' ', ' '], 'ret')
        else:
            # Using .format()
            return "ERROR: Invalid single-word command '{}'. Use 'status', 'off', 'rhon', or 'rhoff'.".format(a)

    elif a == 'h' and b is not None and c is None:
        # Raw Hex Command: h <hex_string>
        if len(b) == 34:
            cm = [a, b]
            return run_com(cm, 'ret')
        else:
            return "ERROR: Raw hex command must be exactly 34 characters long."

    elif a is not None and b is not None and c is not None:
        # Three-part command: <mode> <speed> <bypass>
        cm = [a, b, c]
        if ''.join(cm) in COM_VALID:
            return run_com(cm, 'ret')
        else:
            # Using .format()
            return "ERROR: Invalid 3-part command combination: {} {} {}".format(a, b, c)

    else:
        return "ERROR: Invalid command structure. Check arguments."

# --- Simple CLI logic for direct execution (preserved) ---

if __name__ == '__main__':
    # This part allows the script to be run directly from the terminal
    if len(sys.argv) == 2 and sys.argv[1] == 'help':
        list_helh = [
        "status       view current status",
        "n 1 auto     mode: normal; speed: 1; bypass: auto;",
        "n 2 auto     mode: normal; speed: 2; bypass: auto;",
        "n 3 auto     mode: normal; speed: 3; bypass: auto;",
        "n 1 on       mode: normal; speed: 1; bypass: on;",
        "n 2 on       mode: normal; speed: 2; bypass: on;",
        "n 3 on       mode: normal; speed: 3; bypass: on;",
        "n 1 off      mode: normal; speed: 1; bypass:  off;",
        "n 2 off      mode: normal; speed: 2; bypass: off;",
        "n 3 off      mode: normal; speed: 3; bypass: off;",
        "ne 1 auto    mode: normal exhaust; speed: 1; bypass: auto;",
        "ne 3 auto    mode: normal exhaust; speed: 3; bypass: auto;",
        "ne 1 on      mode: normal exhaust; speed: 1; bypass: on;",
        "ne 3 on      mode: normal exhaust; speed: 3; bypass: on;",
        "ne 1 off     mode: normal exhaust; speed: 1; bypass: off;",
        "ne 3 off     mode: normal exhaust; speed: 3; bypass: off;",
        "ns 1 auto    mode: normal supply; speed: 1; bypass: auto;",
        "ns 3 auto    mode: normal supply; speed: 3; bypass: auto;",
        "ns 1 on      mode: normal supply; speed: 1; bypass: on;",
        "ns 3 on      mode: normal supply; speed: 3; bypass: on;",
        "ns 1 off     mode: normal supply; speed: 1; bypass: off;",
        "ns 3 off     mode: normal supply; speed: 3; bypass: off;",
        "s 1 auto     mode: save; speed: 1; bypass: auto;",
        "s 2 auto     mode: save; speed: 2; bypass: auto;",
        "s 3 auto     mode: save; speed: 3; bypass: auto;",
        "s 1 on       mode: save; speed: 1; bypass: on;",
        "s 2 on       mode: save; speed: 2; bypass: on;",
        "s 3 on       mode: save; speed: 3; bypass: on;",
        "s 1 off      mode: save; speed: 1; bypass: off;",
        "s 2 off      mode: save; speed: 2; bypass: off;",
        "s 3 off      mode: save; speed: 3; bypass: off;",
        "se 1 auto    mode: save exhaust; speed: 1; bypass: auto;",
        "se 3 auto    mode: save exhaust; speed: 3; bypass: auto;",
        "se 1 on      mode: save exhaust; speed: 1; bypass: on;",
        "se 3 on      mode: save exhaust; speed: 3; bypass: on;",
        "se 1 off     mode: save exhaust; speed: 1; bypass: off;",
        "se 3 off     mode: save exhaust; speed: 3; bypass: off;",
        "ss 1 auto    mode: save supply; speed: 1; bypass: auto;",
        "ss 3 auto    mode: save supply; speed: 3; bypass: auto;",
        "ss 1 on      mode: save supply; speed: 1; bypass: on;",
        "ss 3 on      mode: save supply; speed: 3; bypass: on;",
        "ss 1 off     mode: save supply; speed: 1; bypass: off;",
        "ss 3 off     mode: save supply; speed: 3; bypass: off;",
        "off          turn off recuperator",
        "rhoff        turn off the relative humidity display",
        "rhon         turn on the relative humidity"
        ]
        print('Available commands:')
        for p in list_helh: print (p)
        if ser and ser.is_open: ser.close()
        sys.exit()

    try:
        # For simplicity, emulate the original CLI behavior
        if len(sys.argv) == 2:
            result = fhbq_start(sys.argv[1])
            if sys.argv[1] == 'status':
                s = result
                # Using .format()
                print("mode: {}; speed: {}; bypass: {};".format(s.get('mode'), s.get('speed'), s.get('bypass')))
            elif result.get('answer') == 'OK_SENT':
                print('DONE')
            elif result.get('answer') == 'ERROR':
                # Using concatenation
                print(bcolors.FAIL + 'ERROR: ' + str(result) + bcolors.ENDC)
            else:
                print(result)

        elif len(sys.argv) == 3:
            # Hex command
            result = fhbq_start(sys.argv[1], sys.argv[2])
            if result.get('answer') == 'ERROR':
                # Using concatenation
                print(bcolors.FAIL + str(result) + bcolors.ENDC)
            elif result.get('answer') == 'SENT':
                run_com([sys.argv[1], sys.argv[2]], None)
            else:
                print(result)

        elif len(sys.argv) == 4:
            # Three-part command
            result = fhbq_start(sys.argv[1], sys.argv[2], sys.argv[3])
            if result.get('answer') == 'OK_SENT':
                print('DONE')
            elif result.get('answer') == 'ERROR':
                # Using concatenation
                print(bcolors.FAIL + 'ERROR: ' + str(result) + bcolors.ENDC)
            else:
                print(result)
        else:
            # Using concatenation
            print(bcolors.FAIL + "ERROR: Invalid command structure. See help." + bcolors.ENDC)

    except Exception as e:
        # Using .format()
        print(bcolors.FAIL + "An unexpected error occurred: {}".format(e) + bcolors.ENDC)
    finally:
        if ser and ser.is_open:
            ser.close()
