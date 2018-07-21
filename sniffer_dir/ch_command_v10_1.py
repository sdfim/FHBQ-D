#!/usr/bin/env python

import serial
import datetime 
import time 
import sys



s_port = '/dev/ttyUSB0'
b_rate = 9600
#print_checking = 'no'
print_checking = 'yes'
print_preinfo = 'no'
#print_preinfo = 'yes'
print_unit = "no"
#print_unit = "yes"
print_past = 'no'
#print_past = 'yes'
max_send = 5

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

#reading incoming bytes on serial
def read_serial(q):
	#open serial
	ser = serial.Serial(port='/dev/ttyUSB0')
	while True:
		data = ser.read()
		if data == '\x7e':
			data = data + ser.read()       
			if data == '\x7e\x7e':
				if 	q == 'hex':
					data = data + ser.read(15)
					return data
				else:
					data = data + ser.read(2) 
					if 	(q == 'revise' and data == '\x7e\x7e\xc0\xff'):
						data = data + ser.read(13)
						return data
					if 	(q == 'start' and data == '\x7e\x7e\x00\xa0'):
						data = data + ser.read(13)
						return data
					if 	(q == 'unit' and data == '\x7e\x7e\xa0\x00'):
						data = data + ser.read(13)
						return data
				

#converting bytes on serial to dic
def get_dic(data):
	dic = []
	for el in data:
		dic.append(el.encode("hex"))
	return dic

def HexToByte( hexStr ):
    bytes = []
    hexStr = ''.join( hexStr.split(" ") )
    for i in range(0, len(hexStr), 2):
        bytes.append( chr( int (hexStr[i:i+2], 16 ) ) )
    return ''.join( bytes )
	
#checking sended
def checking_sended(send, rev):
	while True:
		#print 'checkinng'
		check = get_dic(read_serial('revise'))
		del check[16]
		
		if print_unit == "yes": 
			unit = get_dic(read_serial('unit'))
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
			if print_preinfo == 'yes': print bcolors.OKGREEN + bcolors.BOLD + 'OK' + bcolors.ENDC
			ch = 'OK'
		else: 
			if print_preinfo == 'yes': print bcolors.FAIL +  "ERROR: something went wrong" + bcolors.ENDC
			ch = 'ERROR'
		
		if print_checking == 'yes':
			print bcolors.WARNING + '                                  bp sp      mode     ' + bcolors.ENDC

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
			print 'sended:  ' + str_sended
			if print_unit == "yes": print 'unit:    ' + str_unit
			print 'checking:' + str_checking
			
			if print_past == 'yes':
				i=1
				while i <= 3:
					print '       ' + ' '.join(get_dic(read_serial('hex')))
					i += 1
		
		return ch

#reading current status for output
def read_status():
    while True:
		rx = get_dic(read_serial('revise'))
		#sys.exit()
		if (rx[9] == '0a' or rx[9] == '2a' or rx[9] == '4a'):
			status = 'off'
			break
		else:
			if rx[9] == '8a': bypass = 'bypass: auto; '
			if rx[9] == 'aa': bypass = 'bypass: on; '
			if rx[9] == 'ca': bypass = 'bypass: off; '
			if rx[13] == '00':
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
    return status

#runing command
def run_com(cm):
	start_time = time.time()
	while True:
		if cm[0] == 'h':
			com = cm[1]
			com = HexToByte(com)
			print bcolors.WARNING + '                                  bp sp      mode     ' + bcolors.ENDC
			print 'get:   ' + ' '.join(get_dic(read_serial('start')))
			#print 'get:   ' + ' '.join(get_dic(read_serial('unit')))
			print 'send:  ' + ' '.join(get_dic(com))
			ser = serial.Serial(port='/dev/ttyUSB0')
			ser.write(com)
			print 'answear'
			i=1
			while i <= 12:
				if i % 3 == 0: print
				print '       ' + ' '.join(get_dic(read_serial('hex')))
				i += 1
			break
		else:
			rx = get_dic(read_serial('revise'))
			rev = []
			rev.extend(rx)	
			rx[2] = '00'
			rx[3] = 'a0'
			if cm[0] == 'off': 
				if rx[9] == '8a': rx[9] = '0a'
				if rx[9] == 'aa': rx[9] = '2a'
				if rx[9] == 'ca': rx[9] = '4a'
			elif (cm[0] == 'rhoff' and (rx[9] == '8a' or rx[9] == 'aa' or rx[9] == 'ca')):
				print 'use rhoff'
				rx[11] = '40'
			elif (cm[0] == 'rhon' and (rx[9] == '8a' or rx[9] == 'aa' or rx[9] == 'ca')):
				print 'use rhon'
				rx[11] = 'd0'
			else:
				if cm[2] == 'auto': rx[9] = '8a'	#'bypass: auto; '
				if cm[2] == 'on': rx[9] = 'aa'		#'bypass: on; '
				if cm[2] == 'off': rx[9] = 'ca'		#'bypass: off; '
				if (cm[0] == 'n' or cm[0] == 'ne' or cm[0] == 'ns'):
					rx[13] = '00'
					if (cm[0] == 'n' and cm[1] == '1'): rx[10] = '0c'		#'mode: normal; speed: 1; '
					if (cm[0] == 'n' and cm[1] == '2'): rx[10] = '12'		#'mode: normal; speed: 2; '
					if (cm[0] == 'n' and cm[1] == '3'): rx[10] = '21'		#'mode: normal; speed: 3; '
					if (cm[0] == 'ne' and cm[1] == '1'): rx[10] = '4a'		#'mode: normal exhaust; speed: 1; '
					if (cm[0] == 'ne' and cm[1] == '3'): rx[10] = '51'		#'mode: normal exhaust; speed: 3; '
					if (cm[0] == 'ns' and cm[1] == '1'): rx[10] = '94'		# 'mode: normal supply; speed: 1; '
					if (cm[0] == 'ns' and cm[1] == '3'): rx[10] = 'a2'		#'mode: normal supply; speed: 3; '
				if (cm[0] == 's' or cm[0] == 'se' or cm[0] == 'ss'):
					rx[13] = '10'
					if (cm[0] == 's' and cm[1] == '1'): rx[10] = '0c'		#'mode: save; speed: 1; '
					if (cm[0] == 's' and cm[1] == '2'): rx[10] = '12'		#'mode: save; speed: 2; '
					if (cm[0] == 's' and cm[1] == '3'): rx[10] = '21'		#'mode: save; speed: 3; '
					if (cm[0] == 'se' and cm[1] == '1'): rx[10] = '4a'		#'mode: save exhaust; speed: 1; '
					if (cm[0] == 'se' and cm[1] == '3'): rx[10] = '51'		#'mode: save exhaust; speed: 3; '
					if (cm[0] == 'ss' and cm[1] == '1'): rx[10] = '94'		#'mode: save supply; speed: 1; '
					if (cm[0] == 'ss' and cm[1] == '3'): rx[10] = 'a2'		#'mode: save supply; speed: 3; '
			
			del rx[16]
			del rev[16]
			packet = HexToByte(''.join(rx))
			
			checksum = 0
			for el in packet:
				checksum ^= ord(el)
			checksum = chr(checksum).encode("hex")
			
			com = ''.join(rx)+checksum
			
			#print com
			com = HexToByte(com)
			
			answer = ''
			i = 1
			ser = serial.Serial(port='/dev/ttyUSB0')
			while answer != "OK":
				get_dic(read_serial('start'))
				#print 'run command'
				if i > max_send: break
				ser.write(com)
				answer = checking_sended(rx, rev)
				i += 1
						
			if print_checking == 'yes': 
				print str(i-1) + ' attempts of send '+ " %s seconds  " % (time.time() - start_time)
				
			break
		
	if print_preinfo == 'yes': print bcolors.WARNING + 'current status: ' + bcolors.ENDC + bcolors.OKBLUE + bcolors.BOLD + read_status() + bcolors.ENDC
	if cm[0] != 'h':
		if answer != "OK": print bcolors.WARNING + bcolors.BOLD + 'ERROR' + bcolors.ENDC
		if answer == "OK": print bcolors.OKGREEN + bcolors.BOLD + 'DONE' + bcolors.ENDC
	#sys.exit()
    

