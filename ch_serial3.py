#!/usr/bin/env python3

import binascii
import codecs 
import time
import serial 
import sys

start_time = time.time()

s_port = '/dev/ttyUSB0'
b_rate = 9600
#open serial
ser = serial.Serial(port=s_port,
    #baudrate=b_rate,
    #timeout=0.5
)

#print_checking = 'no'
print_checking = 'yes'

print_preinfo = 'no'
#print_preinfo = 'yes'

print_unit = "no"
#print_unit = "yes"

print_past = 'no'
#print_past = 'yes'

max_send = 10

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
#get to the right position
def get_position(ser):
    print ('get_position run')
    while True:
        data = ser.read()
        if data == b'\x7e':
            data = data + ser.read()       
            if data == b'\x7e\x7e':
                data = data + ser.read(2) 
                #if (data == b'\x7e\x7e\xc0\xff'):
                #if (data == b'\x7e\x7e\x00\xa0'):
                if (data == b'\x7e\x7e\xa0\x00'):
                    data = data + ser.read(13)
                    data = ser.read(17)
                    break

#reading incoming bytes on serial
def read_serial(ser, q):
    while True:
        data = ser.read()
        if data == b'\x7e':
            data = data + ser.read()       
            if data == b'\x7e\x7e':
                if     q == 'hex':
                    data = data + ser.read(15)
                    return data
                else:
                    data = data + ser.read(2) 
                    if     (q == 'revise' and data == b'\x7e\x7e\xc0\xff'):
                        data = data + ser.read(13)
                        return data
                    if     (q == 'start' and data == b'\x7e\x7e\x00\xa0'):
                        data = data + ser.read(13)
                        return data
                    if     (q == 'unit' and data == b'\x7e\x7e\xa0\x00'):
                        data = data + ser.read(13)
                        return data
                

#converting bytes on serial to dic
def get_dic(data):
    data = data.hex()
    dic = []
    i = 0
    el_n = ''
    for el in data:
        if i%2 != 0:
            el_n = el_n + str(el)
            dic.append(el_n)
            el_n = ''
        else:
            el_n = el_n + str(el)
        i=i+1
    return dic


def HexToByte( hexStr ):
    bytes = []
    hexStr = ''.join( hexStr.split(" ") )
    for i in range(0, len(hexStr), 2):
        bytes.append( chr( int (hexStr[i:i+2], 16 ) ) )
    return ''.join( bytes )
    
#getting checksum for packet hex 
def get_checksum(packet):
    checksum = 0
    for el in packet:
        checksum ^= ord(el)
    checksum = str(list(hex(checksum))[2]) + str(list(hex(checksum))[3])
    print ('checksum = ' + checksum)
    return checksum

#checking sended
def checking_sended(send, rev):
    while True:
        #print ('checkinng')
        check = get_dic(read_serial(ser, 'revise'))
        del check[16]
        
        if print_unit == "yes": 
            unit = get_dic(read_serial(ser, 'unit'))
            #del unit[16]
            
        j = 4
        sum_check = 0
        diff = []
        while j < 16:
            if check[j] == send[j]: 
                sum_check += 1
            if rev[j] != send[j]:
                diff.extend([j])
            j += 1
        
        if sum_check == 12: 
            if print_preinfo == 'yes': print (bcolors.OKGREEN + bcolors.BOLD + 'OK' + bcolors.ENDC)
            ch = 'OK'
        else: 
            if print_preinfo == 'yes': print (bcolors.FAIL +  "ERROR: something went wrong" + bcolors.ENDC)
            ch = 'ERROR'
        
        if print_checking == 'yes':
            print (bcolors.WARNING + '                                  bp sp      mode     ' + bcolors.ENDC)
            #print ('sended:   ', send)
            #print ('checking: ', check)
            #print ('sended:   ' + ' '.join(send))
            #print ('checking: ' + ' '.join(check))
            j = 2
            str_sended = ''
            str_checking = ''
            str_unit = ''
            while j < 16:
                if j in diff:
                    str_sended = str_sended + ' ' + bcolors.WARNING + bcolors.BOLD + str(send[j]) + bcolors.ENDC 
                    if ch == 'OK':
                        str_checking = str_checking + ' ' + bcolors.OKGREEN + bcolors.BOLD + str(check[j]) + bcolors.ENDC
                    if ch == 'ERROR':
                        str_checking = str_checking + ' ' + bcolors.FAIL + bcolors.BOLD + str(check[j]) + bcolors.ENDC 
                elif j == 3:
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
            
            if print_past == 'yes':
                i=1
                while i <= 3:
                    print ('       ' + ' '.join(get_dic(read_serial(ser, 'hex'))))
                    i += 1
            
            #sended = ' '.join(send)
            #sended = sended.replace('7e 7e ','')
            #sended = sended.replace('00 a0 ','00 a0 -> ')
            #print ('sended:   ' + sended)
            #checking = ' '.join(check)
            #checking = checking.replace('7e 7e ','')
            #checking = checking.replace('c0 ff ', 'c0 ff -> ')
            #print ('checking: ' + checking)
        
        return ch

#reading current status for output
def read_status(ser):
    while True:
        rx = get_dic(read_serial(ser, 'revise'))
        #sys.exit()
        if (rx[9] == '0a' or rx[9] == '2a' or rx[9] == '4a'):
            status = 'off'
            break
        else:
            if rx[9] == '8a': bypass = 'bypass: auto; '
            if rx[9] == 'aa': bypass = 'bypass: on; '
            if rx[9] == 'ca': bypass = 'bypass: off; '
            if (rx[13] == '00' or rx[13] == '20'):
                if rx[10] == '0c': mode = 'mode: normal; speed: 1; '
                if rx[10] == '12': mode = 'mode: normal; speed: 2; '
                if rx[10] == '21': mode = 'mode: normal; speed: 3; '
                if rx[10] == '4a': mode = 'mode: normal exhaust; speed: 1; '
                if rx[10] == '51': mode = 'mode: normal exhaust; speed: 3; '
                if rx[10] == '94': mode = 'mode: normal supply; speed: 1; '
                if rx[10] == 'a2': mode = 'mode: normal supply; speed: 3; '
            if rx[13] == '10':
                if rx[10] == '0c': mode = 'mode: save; speed: 1; '
                if rx[10] == '12': mode = 'mode: save; speed: 2; '
                if rx[10] == '21': mode = 'mode: save; speed: 3; '
                if rx[10] == '4a': mode = 'mode: save exhaust; speed: 1; '
                if rx[10] == '51': mode = 'mode: save exhaust; speed: 3; '
                if rx[10] == '94': mode = 'mode: save supply; speed: 1; '
                if rx[10] == 'a2': mode = 'mode: save supply; speed: 3; '
        status = mode + bypass
        break
    print (" %s seconds  " % (time.time() - start_time))
    return status

#runing command
def run_com(ser, cm):
    while True:
        if cm[0] == 'h':
            com = cm[1]
            com = HexToByte(com)
            print (bcolors.WARNING + '                                  bp sp      mode     ' + bcolors.ENDC)
            #print ('get:   ' + ' '.join(get_dic(read_serial(ser, 'revise'))))
            print ('get:   ' + ' '.join(get_dic(read_serial(ser, 'start'))))
            #print ('get:   ' + ' '.join(get_dic(read_serial(ser, 'unit'))))
            print ('send:  ' + ' '.join(get_dic(com)))
            ser.write(com)
            print ('answear')
            i=1
            while i <= 12:
                if i % 3 == 0: print
                print ('       ' + ' '.join(get_dic(read_serial(ser, 'hex'))))
                i += 1
            break
        else:
            rx = get_dic(read_serial(ser, 'revise'))
            rev = []
            rev.extend(rx)    
            rx[2] = '00'
            rx[3] = 'a0'
            if cm[0] == 'off': 
                if rx[9] == '8a': rx[9] = '0a'
                if rx[9] == 'aa': rx[9] = '2a'
                if rx[9] == 'ca': rx[9] = '4a'
            elif (cm[0] == 'rhoff' and (rx[9] == '8a' or rx[9] == 'aa' or rx[9] == 'ca')):
                print ('use rhoff')
                rx[11] = '40'
            elif (cm[0] == 'rhon' and (rx[9] == '8a' or rx[9] == 'aa' or rx[9] == 'ca')):
                print ('use rhon')
                rx[11] = 'd0'
            else:
                if cm[2] == 'auto': rx[9] = '8a'    #'bypass: auto; '
                if cm[2] == 'on': rx[9] = 'aa'        #'bypass: on; '
                if cm[2] == 'off': rx[9] = 'ca'        #'bypass: off; '
                if (cm[0] == 'n' or cm[0] == 'ne' or cm[0] == 'ns'):
                    rx[13] = '20'
                    #rx[13] = '00'
                    if (cm[0] == 'n' and cm[1] == '1'): rx[10] = '0c'        #'mode: normal; speed: 1; '
                    if (cm[0] == 'n' and cm[1] == '2'): rx[10] = '12'        #'mode: normal; speed: 2; '
                    if (cm[0] == 'n' and cm[1] == '3'): rx[10] = '21'        #'mode: normal; speed: 3; '
                    if (cm[0] == 'ne' and cm[1] == '1'): rx[10] = '4a'        #'mode: normal exhaust; speed: 1; '
                    if (cm[0] == 'ne' and cm[1] == '3'): rx[10] = '51'        #'mode: normal exhaust; speed: 3; '
                    if (cm[0] == 'ns' and cm[1] == '1'): rx[10] = '94'        # 'mode: normal supply; speed: 1; '
                    if (cm[0] == 'ns' and cm[1] == '3'): rx[10] = 'a2'        #'mode: normal supply; speed: 3; '
                if (cm[0] == 's' or cm[0] == 'se' or cm[0] == 'ss'):
                    rx[13] = '10'
                    if (cm[0] == 's' and cm[1] == '1'): rx[10] = '0c'        #'mode: save; speed: 1; '
                    if (cm[0] == 's' and cm[1] == '2'): rx[10] = '12'        #'mode: save; speed: 2; '
                    if (cm[0] == 's' and cm[1] == '3'): rx[10] = '21'        #'mode: save; speed: 3; '
                    if (cm[0] == 'se' and cm[1] == '1'): rx[10] = '4a'        #'mode: save exhaust; speed: 1; '
                    if (cm[0] == 'se' and cm[1] == '3'): rx[10] = '51'        #'mode: save exhaust; speed: 3; '
                    if (cm[0] == 'ss' and cm[1] == '1'): rx[10] = '94'        #'mode: save supply; speed: 1; '
                    if (cm[0] == 'ss' and cm[1] == '3'): rx[10] = 'a2'        #'mode: save supply; speed: 3; '
            
            del rx[16]
            del rev[16]
            packet = HexToByte(''.join(rx))
            
            checksum = get_checksum(packet)
           
            com = ''.join(rx)+checksum
            com_print = com
            
            answer = ''
            i = 1
            while answer != "OK":
                get_dic(read_serial(ser, 'start'))
                #print ('run command ' + com_print)
                if (i%2 != 0  and i != 1): get_position(ser)
                if i > max_send: break
                ser.write(codecs.decode(com, 'hex_codec'))
                answer = checking_sended(rx, rev)
                i += 1
                        
            if print_checking == 'yes': 
                print (str(i-1) + ' attempts of send '+ " %s seconds  " % (time.time() - start_time))
                
            break
        
    if print_preinfo == 'yes': print (bcolors.WARNING + 'current status: ' + bcolors.ENDC + bcolors.OKBLUE + bcolors.BOLD + read_status(ser) + bcolors.ENDC)
    if cm[0] != 'h':
        if answer != "OK": print ('ERROR')
        if answer == "OK": print ('DONE')
    sys.exit()
    


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

com_valid=[
"n1auto", "n2auto", "n3auto", "n1on", "n2on", "n3on", "n1off", "n2off", "n3off", 
"ne1auto", "ne3auto", "ne1on", "ne3on", "ne1off", "ne3off", 
"ns1auto", "ns3auto", "ns1on", "ns3on", "ns1off", "ns3off", 
"s1auto", "s2auto", "s3auto", "s1on", "s2on", "s3on", "s1off", "s2off", "s3off", 
"se1auto", "se3auto", "se1on", "se3on", "se1off", "se3off", 
"ss1auto", "ss3auto", "ss1on", "ss3on", "ss1off", "ss3off"]

if len(sys.argv) == 2:
    if sys.argv[1] == 'status':
        #print (bcolors.OKBLUE + bcolors.BOLD + read_status(ser) + bcolors.ENDC)
        print (read_status(ser))
        sys.exit()
    if (sys.argv[1] == 'off' or sys.argv[1] == 'rhoff' or sys.argv[1] == 'rhon'):
           run_com(ser, [sys.argv[1], ' ', ' '])
           sys.exit()
    if sys.argv[1] == 'help':
        print ('posiple/valid command: ')
        for p in list_helh: print (p)
        sys.exit()
elif len(sys.argv) == 3:
    if sys.argv[1] == 'h':
        if len(sys.argv[2]) == 34:
            cm = [sys.argv[1], sys.argv[2]]
            run_com(ser, cm)
elif len(sys.argv) == 4:
    cm = [sys.argv[1], sys.argv[2], sys.argv[3]]
    if ''.join(cm) in com_valid:
        run_com(ser, cm)
    else:
        print (bcolors.FAIL + "ERROR: Your team is not valid, see help" + bcolors.ENDC)
        sys.exit()
else:
    print (bcolors.FAIL + "ERROR: Your team is not valid, see help" + bcolors.ENDC)
    sys.exit()
