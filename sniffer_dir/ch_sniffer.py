#!/usr/bin/env python

import time 
import sys
from ch_command_v10_1 import*

start_time_all = time.time()

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    

i=1
while i <= 100:
	print '       ' + ' '.join(get_dic(read_serial('hex')))
	i += 1


print " %s seconds  " % (time.time() - start_time_all)
sys.exit()
