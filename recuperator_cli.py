#!/usr/bin/env python3

# Required libraries for serial communication, encoding, timing, and system interaction
import binascii
import codecs
import time
import serial
import sys
from pprint import pprint

# Record the start time of the script for execution time measurement
start_time = time.time()

# Serial port configuration
s_port = '/dev/ttyUSB0'
b_rate = 9600

# Open serial port with robust error handling
try:
    # Initialize and open the serial connection
    ser = serial.Serial(port=s_port,
        #baudrate=b_rate,
        #timeout=0.5
    )
except serial.SerialException as e:
    # Print error message and exit if the port cannot be opened (e.g., device disconnected)
    print("ERROR: Could not open serial port {}. Make sure the device is connected and the port is correct ({})".format(s_port, e))
    sys.exit(1)


# Flags to control console output verbosity
# Set to 'no' for silent mode, or 'yes' to show detailed debugging info
print_checking = 'no'
# print_checking = 'yes'

# print_preinfo = 'no'
print_preinfo = 'no'

# print_unit = "no"
print_unit = "no"

# print_past = 'no'
print_past = 'no'

# Maximum number of times to attempt sending a command
max_send = 10

# ANSI color codes for stylized console output
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Function to synchronize with the communication protocol stream.
# Reads bytes until it finds the start sequence (\x7e\x7e\xa0\x00), then consumes the rest of the packet.
def get_position():
    print ('get_position run')
    while True:
        data = ser.read()
        if data == b'\x7e':
            data = data + ser.read()
            if data == b'\x7e\x7e':
                data = data + ser.read(2)
                # This specific header (\xa0\x00) signals the unit's status packet, used for synchronization
                if (data == b'\x7e\x7e\xa0\x00'):
                    data = data + ser.read(13)
                    data = ser.read(17)
                    break

# Reads a full packet from the serial port based on the expected header type (q)
def read_serial(q):
    while True:
        data = ser.read()
        if data == b'\x7e':
            data = data + ser.read()
            if data == b'\x7e\x7e':
                # If 'hex' is requested, read the next 15 bytes regardless of header
                if     q == 'hex':
                    data = data + ser.read(15)
                    return data
                else:
                    data = data + ser.read(2)
                    # 'revise' header: ACK/Status packet from unit
                    if     (q == 'revise' and data == b'\x7e\x7e\xc0\xff'):
                        data = data + ser.read(13)
                        return data
                    # 'start' header: Command initiation packet (sent by control panel)
                    if     (q == 'start' and data == b'\x7e\x7e\x00\xa0'):
                        data = data + ser.read(13)
                        return data
                    # 'unit' header: Device status packet (used in get_position)
                    if     (q == 'unit' and data == b'\x7e\x7e\xa0\x00'):
                        data = data + ser.read(13)
                        return data


# Converts a bytes object (packet) into a list of two-character hexadecimal strings
def get_dic(data):
    dic = []
    for el in data:
        # Format byte to two-character hex string (e.g., 10 -> '0a')
        nel = '{:02x}'.format(el)
        dic.append(nel)
    return dic

# Converts a space-separated hex string (e.g., '7e 7e 00 a0') into raw bytes
def HexToByte( hexStr ):
    hexStr = ''.join( hexStr.split(" ") )
    return codecs.decode(hexStr, 'hex_codec')

# Calculates the checksum (XOR sum) of all bytes in the packet body
def get_checksum(packet):
    checksum = 0
    # Iterate through each byte and apply the XOR operation
    for el in packet:
        checksum ^= el
    # Format the final checksum as a two-character hex string
    checksum_hex = '{:02x}'.format(checksum)

    # OUTPUT CONTROL: Print checksum only if print_checking is 'yes'
    if print_checking == 'yes':
        print ('checksum = ' + checksum_hex)

    return checksum_hex

# Validates if the command was successfully acknowledged by the unit
def checking_sended(send, rev):

    # OUTPUT CONTROL: Print initial revision packet only if print_checking is 'yes'
    if print_checking == 'yes':
        print("!!! rev = ", rev)

    # Attempt to read the ACK (status/revise) packet following the command send
    try:
        check = get_dic(read_serial('revise'))
    except Exception as e:
        # Handle failure to read the expected ACK packet
        print("Error reading ACK: {}".format(e))
        return 'ERROR'

    del check[16] # Remove checksum from the received packet list

    if print_unit == "yes":
        unit = get_dic(read_serial('unit'))

    # Logic to compare the sent packet (send) with the received ACK (check)
    j = 4
    sum_check = 0
    diff = []

    # Iterate over data fields (bytes 4 through 15)
    while j < 16:
        # Check for matching bytes (sent data echoed back)
        if check[j] == send[j]:
            sum_check += 1

        # Track differences between the received ACK and the status *before* the command (rev)
        if rev[j] != check[j]:
            diff.extend([j])
        j += 1

    # Assume success if a valid ACK packet was received
    ch = 'OK_SENT'

    # Detailed logging for debugging packets (controlled by print_checking)
    if print_checking == 'yes':
        print ("!!! sum_check =", sum_check)

        print (bcolors.WARNING + '                                  bp sp      mode     ' + bcolors.ENDC)
        j = 2
        str_sended = ''
        str_checking = ''
        str_unit = ''

        # Display the packets with color highlighting changes
        while j < 16:
            if j in diff:
                # Highlight bytes that changed since the original status (rev)
                str_sended = str_sended + ' ' + bcolors.WARNING + bcolors.BOLD + str(send[j]) + bcolors.ENDC
                str_checking = str_checking + ' ' + bcolors.OKGREEN + bcolors.BOLD + str(check[j]) + bcolors.ENDC
            elif j == 3:
                # Add separator after header bytes
                str_sended = str_sended + ' ' + str(send[j]) + ' ->'
                str_checking = str_checking + ' ' + str(check[j]) + ' ->'
                if print_unit == "yes": str_unit = str_unit + ' ' + str(unit[j]) + ' ->'
            else:
                str_sended = str_sended + ' ' + str(send[j])
                str_checking = str_checking + ' ' + str(check[j])
                if print_unit == "yes": str_unit = str_unit + ' ' + str(unit[j])
            j += 1

        print ('sended:  ' + str_sended)
        if print_unit == "yes": print ('unit:    ' + str_unit)
        print ('checking:' + str_checking)

        # Print subsequent raw packets for low-level debugging
        if print_past == 'yes':
            i=1
            while i <= 3:
                print ('       ' + ' '.join(get_dic(read_serial('hex'))))
                i += 1

    return ch # Returns 'OK_SENT' if ACK was received, 'ERROR' otherwise

# Reads the current operational status from the unit and translates hex codes into human-readable strings
def read_status():
    # Loop to ensure a valid status packet is captured
    while True:
        try:
            rx = get_dic(read_serial('revise'))
            break
        except Exception:
            # If reading fails, resynchronize the port and try again
            get_position()

    # Check if the unit is explicitly turned off (based on byte 9 values)
    if (rx[9] == '0a' or rx[9] == '2a' or rx[9] == '4a'):
        status = 'off'
    else:
        # Decode Bypass mode (byte 9)
        bypass = ''
        if rx[9] == '8a': bypass = 'bypass: auto; '
        if rx[9] == 'aa': bypass = 'bypass: on; '
        if rx[9] == 'ca': bypass = 'bypass: off; '

        # Decode Operation Mode (byte 13) and Speed (byte 10)
        mode = ''
        if (rx[13] == '00' or rx[13] == '20'): # Normal Mode
            if rx[10] == '0c': mode = 'mode: normal; speed: 1; '
            elif rx[10] == '12': mode = 'mode: normal; speed: 2; '
            elif rx[10] == '21': mode = 'mode: normal; speed: 3; '
            # ... and other normal modes
        elif rx[13] == '10': # Save/Eco Mode
            if rx[10] == '0c': mode = 'mode: save; speed: 1; '
            elif rx[10] == '12': mode = 'mode: save; speed: 2; '
            elif rx[10] == '21': mode = 'mode: save; speed: 3; '
            # ... and other save modes

        status = mode + bypass

    # OUTPUT CONTROL: Print execution time only if print_checking is 'yes'
    if print_checking == 'yes':
        print (" %s seconds  " % (time.time() - start_time))

    return status

# Main function to execute a command, handles current status capture, packet creation, sending, and verification
def run_com(cm):

    # 1. Capture current status packet (rev) to use as a base for the command
    while True:
        try:
            rev = get_dic(read_serial('revise'))
            break
        except Exception:
            get_position()

    # 2. Prepare command (rx) based on current status (rev)
    rx = rev[:] # Make a mutable copy of the current status
    del rx[16] # Remove the checksum from the current status (will be recalculated)

    # Set the command packet header (rx[2], rx[3]) from status ('c0', 'ff') to command ('00', 'a0')
    rx[2] = '00'
    rx[3] = 'a0'

    # Logic to translate user arguments (cm) into specific packet bytes
    if cm[0] == 'off':
        # Logic to turn off the unit by modifying byte 9
        if rx[9] == '8a': rx[9] = '0a'
        if rx[9] == 'aa': rx[9] = '2a'
        if rx[9] == 'ca': rx[9] = '4a'
    elif (cm[0] == 'rhoff' and (rx[9] == '8a' or rx[9] == 'aa' or rx[9] == 'ca')):
        print ('use rhoff')
        rx[11] = '40' # Set byte 11 for humidity off
    elif (cm[0] == 'rhon' and (rx[9] == '8a' or rx[9] == 'aa' or rx[9] == 'ca')):
        print ('use rhon')
        rx[11] = 'd0' # Set byte 11 for humidity on
    else:
        # Set Bypass mode (byte 9) based on argument cm[2]
        if cm[2] == 'auto': rx[9] = '8a'
        if cm[2] == 'on': rx[9] = 'aa'
        if cm[2] == 'off': rx[9] = 'ca'

        # Set Normal Mode (byte 13 = '20') and Speed (byte 10) based on arguments cm[0] and cm[1]
        if (cm[0] == 'n' or cm[0] == 'ne' or cm[0] == 'ns'):
            rx[13] = '20'
            if (cm[0] == 'n' and cm[1] == '1'): rx[10] = '0c'
            # ... other Normal mode speed/direction settings

        # Set Save Mode (byte 13 = '10') and Speed (byte 10) based on arguments cm[0] and cm[1]
        if (cm[0] == 's' or cm[0] == 'se' or cm[0] == 'ss'):
            rx[13] = '10'
            if (cm[0] == 's' and cm[1] == '1'): rx[10] = '0c'
            # ... other Save mode speed/direction settings


    # 3. Finalize and send command
    packet_hex_list = rx[:]
    packet_hex = ''.join(packet_hex_list)
    packet_bytes = HexToByte(packet_hex)

    checksum_hex = get_checksum(packet_bytes) # Calculate the checksum (output controlled inside func)
    com = packet_hex + checksum_hex # Final command string including checksum

    answer = ''
    i = 1

    # Retry loop for sending the command until successful acknowledgement or max attempts reached
    while answer != "OK_SENT":

        # Read a 'start' packet before sending command for synchronization
        get_dic(read_serial('start'))

        if (i > 1): get_position() # Resynchronize the port on retries
        if i > max_send:
            answer = "ERROR"
            break

        ser.write(HexToByte(com)) # Send the command bytes
        answer = checking_sended(rx, rev) # Check for ACK (output controlled inside func)
        i += 1

    # 4. Display results
    # OUTPUT CONTROL: Print attempts/time only if print_checking is 'yes'
    if print_checking == 'yes':
        print (str(i-1) + ' attempts of send '+ " %s seconds  " % (time.time() - start_time))

    if print_preinfo == 'yes':
        print (bcolors.WARNING + 'current status: ' + bcolors.ENDC + bcolors.OKBLUE + bcolors.BOLD + read_status() + bcolors.ENDC)

    # Print final success/error message
    if cm[0] != 'h':
        if answer != "OK_SENT": print ('ERROR')
        if answer == "OK_SENT": print ('DONE')

    ser.close()
    sys.exit()

# List of valid commands and their descriptions for the 'help' menu
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

# List of valid command combinations (used for input validation)
com_valid=[
"n1auto", "n2auto", "n3auto", "n1on", "n2on", "n3on", "n1off", "n2off", "n3off",
"ne1auto", "ne3auto", "ne1on", "ne3on", "ne1off", "ne3off",
"ns1auto", "ns3auto", "ns1on", "ns3on", "ns1off", "ns3off",
"s1auto", "s2auto", "s3auto", "s1on", "s2on", "s3on", "s1off", "s2off", "s3off",
"se1auto", "se3auto", "se1on", "se3on", "se1off", "se3off",
"ss1auto", "ss3auto", "ss1on", "ss3on", "ss1off", "ss3off"]

# Command Line Argument Parsing (sys.argv)
if len(sys.argv) == 2:
    if sys.argv[1] == 'status':
        # Execute status check and exit
        print (read_status())
        ser.close()
        sys.exit()
    if (sys.argv[1] == 'off' or sys.argv[1] == 'rhoff' or sys.argv[1] == 'rhon'):
           # Execute one-word commands (off, rhoff, rhon)
           run_com([sys.argv[1], ' ', ' '])
    if sys.argv[1] == 'help':
        # Display the list of valid commands
        print ('posiple/valid command: ')
        for p in list_helh: print (p)
        ser.close()
        sys.exit()
elif len(sys.argv) == 3:
    if sys.argv[1] == 'h':
        # Handle raw hex command input
        if len(sys.argv[2]) == 34:
            cm = [sys.argv[1], sys.argv[2]]
            run_com(cm)
        else:
            # Error for incorrect raw hex command length
            print (bcolors.FAIL + "ERROR: Hex command must be 34 characters long." + bcolors.ENDC)
            ser.close()
            sys.exit()
elif len(sys.argv) == 4:
    # Handle three-part commands (e.g., n 1 auto)
    cm = [sys.argv[1], sys.argv[2], sys.argv[3]]
    if ''.join(cm) in com_valid:
        run_com(cm)
    else:
        # Error for invalid three-part command
        print (bcolors.FAIL + "ERROR: Your team is not valid, see help" + bcolors.ENDC)
        ser.close()
        sys.exit()
else:
    # Error for incorrect number of arguments
    print (bcolors.FAIL + "ERROR: Your team is not valid, see help" + bcolors.ENDC)
    ser.close()
    sys.exit()
