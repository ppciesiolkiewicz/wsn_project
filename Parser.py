#!/usr/bin/python
# vim:set expandtab si:

"""Parser - read from stdin and return dictionary for a given line
ts (time stamp), txP, hops, s (no sensor readings), bat, ir, accy, accx, temp,
hum, node, seq

if self.clean == True:
    Parser returns only valid results
"""

from __future__ import print_function
import pprint
import sys
import re
import getopt
import datetime
from time import time
from datetime import datetime as dt
import parser
import xml.etree.ElementTree as ET


class Stat:
    def __init__(self):
        self.nodes = {}
        self.nodes_list = []
        self.types = {"pkts":1, "unique":1, "via_cnt":1, "zzz_cnt":1}
        self.data = {}
        self.ignored = ["src", "debug2", "ts", "debug1", "dummy", "sensors", "rtc_s"]
        self.viadata = ["rssi", "txP", "lqi", "via_cnt" ]
        self.formats_f = ["batt", "hum", "photo", "ir", "temp", "co2", "dust", "vref"]
        self.colors = {
            "batt":"\033[01;32m", "temp":"\033[01;31m",  "hum":"\033[01;36m",
            "via":"\033[01;33m", "via_cnt":"\033[01;33m", "pkts":"\033[01;33m", "unique":"\033[04;33m",
            "zzz_cnt":"\033[01;33m", 
            "missing":"\033[04;31m" }
        self.c = {
            "red":"\033[01;31m", "green":"\033[01;32m", "yellow":"\033[01;33m",
            "white":"\033[01;37m", "dkgreen":"\033[00;32m", "grey":"\033[01;30m",
            "blue":"\033[00;34m",
            "BG_blue": "\033[01;44m", "BG_green": "\033[01;42m",
            "NORM":"\033[00m" }
        self.last=0
        self.lasttime =0.0
        self.lastts ={}
        self.v=0

    def get_nodes_sequence(self):
        """ return a nodes_list as given with -o option
            and then the rest of the nodes sorted
        """
        return self.nodes_list + [node for node in sorted(self.nodes.keys()) if node not in self.nodes_list]

    def print(self):
        print("\033[H", end="")  ## E.T. Go Home  --> infocmp -L 
        if time()-self.lasttime >=4:
            print("\033[2J", end="")  ## clear screen --> infocmp -L 
            self.lasttime=time()

        # header with node numbers
        print("{:2} Nodes: {}".format(len(self.nodes),self.c["BG_blue"]), end="")
        for i in self.get_nodes_sequence():
            if i==self.v:
                print (self.c["BG_green"], end="")    # mark via message with green header
            if i==self.last:
                print ("{}{:7d}{}".format(self.c["red"],i,self.c["yellow"]), end="")    # mark last message with red header
            else:
                print ("{}{:7d}".format(self.c["yellow"],i), end="")    # normal
            if i==self.v:
                print (self.c["BG_blue"], end="")    # end mark via message with green header
        print(self.c["NORM"])

        # measurements
        for i in sorted(self.types):
            try: print("{}{:10}{}".format(self.colors[i],i,self.c["NORM"]), end="")
            except KeyError: print("{:10}".format(i), end="")
            for n in self.get_nodes_sequence():
                if n==self.last:
                    try: print(self.colors[i], end="")
                    except KeyError: print (self.c["white"], end="")   # highlight last message (01;37m == white)
                if i in self.viadata and n==self.v:
                    print(self.c["dkgreen"], end="")
                if (n,i) in self.data:
                    if i in self.formats_f:
                        print (" {:3.6f}   ".format(self.data[(n,i)])[0:7], end="")
                    else:
                        print ("{:7}".format(self.data[(n,i)]), end="")
                else:
                    print ("      -",  end="")
                if i in self.viadata and n==self.v:
                    print(self.c["NORM"], end="")

                if n==self.last:
                    print (self.c["NORM"], end="") # ... and return to normal colors
            print("")
        print("")
        print("{}{} --- {}{}".format(self.c["blue"], self.lastts, datetime.datetime.now(), self.c["NORM"]))


    def add(self,dic,uniq):
        try:
            n=dic["src"]
        except KeyError:
            return

        self.last=n
        try:
            self.data[(n,"pkts")] += 1
        except KeyError:
            self.data[(n,"pkts")] = 1
            self.data[(n,"unique")] = 0
            self.nodes[n]=n

        if uniq:
            self.data[(n,"unique")] += 1

        try:
            self.v=dic["via"]
            if not self.v==n: ## do not count vias for direct packets
                try:
                    self.data[(self.v,"via_cnt")] += 1
                except KeyError:
                    self.data[(self.v,"via_cnt")] =1
            else:
                try:
                    self.data[(self.v,"zzz_cnt")] += 1
                except KeyError:
                    self.data[(self.v,"zzz_cnt")] =1
        except KeyError:
            self.v=n

        try: seq=dic["seq"]
        except KeyError: seq=0
        try: oldseq=self.data[(n,"seq")]
        except KeyError:
            self.data[(n,"seq")]=seq
            oldseq=seq
        if seq - oldseq>1:
            self.types["missing"]=1
            try: self.data[(n,"missing")] += seq - oldseq - 1
            except KeyError: self.data[(n,"missing")] = seq - oldseq - 1

        for i in dic:
            if i[0:4]!="node":
                if i not in self.ignored:
                    self.types[i]=1   # just in case. Add to list of displayed values
                    if i in self.viadata:
                        self.data[(self.v,i)]=dic[i]  # parameters related to last hop sender
                    else:
                        self.data[(n,i)]=dic[i]       # measurements, related to packet source
        self.lastts=dic["ts"]

class Parser:
    def __init__(self):
        """define constants"""
        self.base = 28
        self.clean = True
        self.unique = False
        self.hex = False
        self.debug = 0
        self.pkg_seq = {}
        self.nodes = []     # if len(nodes) > 0 only accept packets from nodes
                            # on this list
        self.via = []       # if len(via) > 0 only accept packets that came to
                            # BS from nodes on this list
        self.dates = []     # if len(dates) > 0 only accept packets from
                            # specified timeframe
        self.driftcal = {} # drift offset data for each node
        self.lastseq = {}   # last seq for drift calculations
        self.lastdrift = {} # last drift for drift calculations (rests)
        self.msg_types = {'MSG_CMD': 0x01, 'MSG_DATA': 0x02,
            'MSG_ROUTING':0x03, 'MSG_ACK':0x04,
            'MSG_HELLO':0x05, 'MSG_EHLO':0x06,
            'MSG_TIMESYNC':0x07, 'MSG_RESET':0x08,
            'MSG_REQUEST_ACK' : 0x10,
            'MSG_TIMESTAMP': 0x11,
            'CMD_RTDBG':0x21, 'MSG_RTDBG' : 0x22,
            'CMD_SETCFG':0x31,
            'MSG_LOGERASE':0x40,    # erase log and initialize log memory
            'MSG_LOGSTART':0x41,    # start logging to Flash Memory
            'MSG_LOGSTOP':0x42,     # stop logging
            'MSG_SETTIME':0x43,     # set node's time reference value (current time)
            'MSG_GETTIME':0x46,     # get node's time reference value (current time)
            'MSG_LOGREAD':0x44,     # read log by retransmitting entries
            'MSG_LOGINFO':0x45,     # log query response

            'MSG_RNG_SETUP':0x50,
            'MSG_RNG_START':0x51,
            'MSG_RNG_QUERY':0x52,
            'MSG_RNG_PING':0x55,
            'MSG_RNG_READY':0x58,
            'MSG_RNG_RESULTS':0x59,

            'MSG_RESPONSE_PREFIX' : 0x80,
            'MSG_DRIFT' : 0xAA,
            'MSG_OTHER': 0xFF}

    def checkCRC(self,array):
        crc = 0
        index = 1+2          #+2 since two first elements represent date and time, the fird is 7E
        stop = len(array)-4  # -3-1 - 3 last bytes (CRC HI, CRC LO and 7E are skipped; -1 since array is numbered from 0) 
        if stop<index:       # sometimes lines are too short!
            return False

        while (index<=stop):
            #print(array[index])
            byte = int(array[index],16)
            # instead of separate procedur I put the code here to speedup a bit
            # crc = self.crcAddByte(crc, byte)
            crc = crc^(byte<<8)
            for i in range(7, -1, -1):
                if ((crc & 0x8000) == 0x8000):
                    crc = (crc << 1)^0x1021
                else:
                    crc = crc << 1

            index = index+1

        crcHI = (crc & 0xFF00) >> 8;
        crcLO = (crc & 0x00FF)    
        if (crcHI==int(array[len(array)-2], 16)) and (crcLO==int(array[len(array)-3], 16)):
            return True
        else:
            return False


    def new_pkg(self, dic):
        """keep a list of (src,seq) pairs, a new packet from the same src will
        have higher seq number of smaller by at least 4 (in case of a restart)"""
        if len(dic) == 0:
            return False
        try:
            if dic["seq"] > self.pkg_seq[dic["src"]]:
                self.pkg_seq[dic["src"]] = dic["seq"]
                return True
            elif dic["seq"] + 4 < self.pkg_seq[dic["src"]]:
                self.pkg_seq[dic["src"]] = dic["seq"]
                return True
            else:
                return False
        except KeyError:
            try: self.pkg_seq[dic["src"]] = dic["seq"]
            except KeyError: return True
            return True

    def parse_sensor(self, sensor_bytes):
        """ return value based on sensor type and data
        sensor bytes are hex-encoded and in a list, first element is the sensor type
        >>> parse_sensor(['01', '01', '01'])
        ('batt', 123)
        """
        try:
            t = int(sensor_bytes[0], 16)
            v = 256*int(sensor_bytes[1],16) + int(sensor_bytes[2],16)
        except ValueError as err:
            """ ValueError is possible if the number of sensors is corrupted and
            this function gets wrong data """
            print(err, file=sys.stderr)
            raise

        d = {}
        try:
            if t==1: # Battery
                d["batt"] = 3.0*v/4096
            elif t==2: # Temp
                d["temp"] = -39.6+0.01*v
            elif t==3: 
                d["photo"] = 2.5*v*6250.0/4096.0
            elif t==4: 
               d["ir"] = 1.5*v/4.096
            elif t==5:
               d["hum"] = 0.0405*v -0.0000028 *v*v - 4
            elif t==6:
                d["press"] = v
            elif t==7:
                d["accx"] = v
            elif t==8:
                d["accy"] = v
            elif t==9:
               d["co"] = v
            elif t==10:
                d["co2"] = 2.5*v/4.096-200
            elif t==11:
                d["dust"] = 2.5*v/4096.0+0.03
            elif t==12:
                d["pir"] = v
            elif t==13:
                d["magn"] = v
            elif t==14:
                # d["vref"] = v
                d["vref"] = 3.0*v/4096
            elif t==15:
                d["other"] = v
            elif t==16:
                #d["adc0"] = 3.0*v/4096
                d["ADC0r"] = v
            elif t==17:
                #d["adc1"] = 3.0*v/4096
                d["ADC1r"] = v
            elif t==18:
                #d["adc2"] = 3.0*v/4096
                d["ADC2r"] = v
            elif t==19:
                #d["adc3"] = 3.0*v/4096
                d["ADC3r"] = v
            elif t==240:
                #d["NoOfT"] = v/256
                d["actual"] = int(sensor_bytes[2],16)
            elif t==241:
                d["LenOfTurn"] = v
            elif t==253:
                # get send queue
                d["debug1"] = v
            elif t==254:
                # get path (up to 5 hops)
                d["debug2"] = [int(b,16) for b in sensor_bytes[1:]]
            elif t==255:
                d["debug3"] = v
            elif t==0:
                # TODO: this should be an error actually...
                d["dummy"] = 0.0
            else:
                raise NameError
        except NameError as err:
            print(err, file=sys.stderr)
            print("Unknown sensor type: " + str(t) + " value: " + str(v), file=sys.stderr)
            d["dummy"] = 0.0
        
        except IndexError as err:
            print('parse_sensor: hexdump line probably too small', file=sys.stderr)
            print(err, file=sys.stderr)
            print("bytes: {}".format(sensor_bytes), file=sys.stderr)
            d["dummy"] = 0.0

        return d.keys()[0], d.values()[0]

    def parse_msg_data(self, dic, line, base):
        """ dic is a dictionary with header info -- add payload info 
        base is a displacement of payload in the byte list line"""
        try:
            dic["sensors"] = int(line[base],16)
            sensor_size = 3
            base = base+1
            for sensor in range(dic["sensors"]):
                # pass on 6 bytes instead of 3 for the sake of "debug2" datatype
                k,v = self.parse_sensor(line[base:base+2*sensor_size])
                dic[k] = v
                if k in ['ADC0r', 'ADC1r', 'ADC2r', 'ADC3r']:
                    if k == 'ADC0r':
                        dic['adc0'] = v*0.00062043 #3.0*v/4096.0
                    if k == 'ADC1r':
                        dic['adc1'] = v*0.00062043 #3.0*v/4096.0
                    if k == 'ADC2r':
                        dic['adc2'] = v*0.00062043 #3.0*v/4096.0
                    if k == 'ADC3r':
                        dic['adc3'] = v*0.00062043 #3.0*v/4096.0
                base += sensor_size
        except IndexError as err:
            print('parse_msg_data: hexdump line probably too small', file=sys.stderr)
            print(err, file=sys.stderr)
        except ValueError as err:
            print('parse_msg_data: the number of sensors may be corrupted', file=sys.stderr)
            print(err, file=sys.stderr)
        return dic

    # clock drift measurements, 01.2014
    def parse_drift(self, dic, line, base):

        # handling of rebooted BS node
        try:
            blastcal=0.0
            bdrft = dt.fromtimestamp(0.0009765625 * dic['bstamp']) # 1/1024 * nstamp

            try:
                bcal=self.driftcal[9999]
            except KeyError as err:
                bcal= dic['ts'] - bdrft
                self.driftcal[9999] = bcal
                print(' ### Setting time calibration for BS at {}'.format(bcal))

            bdrft = bdrft + bcal - dic['ts']
            dic['bdrift'] = float(bdrft.total_seconds())

            try:
                blastcal=self.lastdrift[9999]
                if abs(dic['bdrift']-blastcal)>2:
                    # node reset detected, skipped more than 2 secs
                    print(' ### ReSetting BS -- now: {}, last: {}'.format(dic['bdrift'], blastcal))
                    bdrft = dt.fromtimestamp(0.0009765625 * dic['bstamp'] - blastcal)
                    bcal = dic['ts'] - bdrft
                    self.driftcal[9999] = bcal
                    print(' ### ReSetting time calibration for BS at {} ({})'.format( bdrft, blastcal))
                    bdrft = bdrft + bcal - dic['ts']
                    dic['bdrift'] = float(bdrft.total_seconds()) + blastcal
            except KeyError as err:
                pass

            self.lastdrift[9999]=dic['bdrift']


            # handling of rebooted nodes
            nlastcal=0.0
            try:
                if self.lastseq[dic['src']] >= dic['seq']:
                    # node reset detected
                    self.driftcal.pop(dic['src'], None)   # delete key and force recalculation
                    nlastcal=self.lastdrift[dic['src']]
                    print(' ### ReSetting time calibration for node {} at {}'.format(dic['src'], nlastcal))
            except KeyError as err:
                pass

            ndrft = dt.fromtimestamp(0.0009765625 * dic['nstamp'] - nlastcal) # 1/1024 * nstamp
            if (abs(nlastcal)>0.000001):
                    print(' ### ReSet: for node {} at ndrft {} (diff {})'.format(dic['src'], ndrft, nlastcal))
                    print(' ### ReSet: for node {} Non-comp {} (diff {})'.format(dic['src'],  dt.fromtimestamp(0.0009765625 * dic['nstamp']), nlastcal))

            try:
                ncal=self.driftcal[dic['src']]
            except KeyError as err:
                ncal= dic['ts'] - ndrft
                self.driftcal[dic['src']] = ncal
                print(' ### Setting time calibration for node {} at {}'.format(dic['src'], ncal))

            ndrft = ndrft + ncal - dic['ts'] 

            dic['ndrift'] = float(ndrft.total_seconds()) +nlastcal

            self.lastdrift[dic['src']]=dic['ndrift']
            self.lastseq[dic['src']]=dic['seq']
            return dic
        except KeyError as err:
            print('KeyError: ' + str(err))
            print(dic)
            return {}

    def parse_msg_reset(self, dic, line, base):
        """ only payload in MSG_RESET is time to reset [ms] """
        if self.debug>0:
            print("RESET {}".format(line[base:base+2]))
        dic['reset_time'] = 256*int(line[base],16) + int(line[base+1],16)
        return dic

    def parse_msg_hello(self, dic, line, base):
        """ only payload in MSG_HELLO is node_type and dist2BS in hops """
        if self.debug>0:
            print("HELLO {}".format(line[base:base+2]))
        dic['node_type'] = int(line[base],16)
        dic['dst2bs'] = int(line[base+1],16)
        return dic

    def parse_msg_timestamp(self, dic, line, base):
        """ only payload in MSG_TIMESTAMP is a 4-byte timestamp """
        if self.debug:
            print("TIMESTAMP {}".format(line[base:base+2]))
        dic['timestamp'] = 2**24*int(line[base],16) + 2**16*int(line[base+1],16) \
            + 2**8*int(line[base+2],16) + int(line[base+3],16) 
        return dic

    def parse_msg_ehlo(self, dic, line, base):
        """ no payload - return dic """
        if self.debug>0:
            print("EHLLO")
        return dic

    def parse_cmd_rtdbg(self, dic, line, base):
        """ no payload - return dic """
        if self.debug>0:
            print("CMD_RTDBG")
        return dic

    def parse_unknown(self, dic, line, base, what):
        if self.debug>0:
            print('Parsing {}'.format(what))
            print('Base= {}'.format(base))
            print('line={}'.format(line))
        dic['payload'] = '"'+'_'.join(line[base:-3])+'"'
        return dic

    def parse_setgettime(self, dic, line, base, what):
        """ SET and GET time share common format """
        if self.debug>0:
            print('Parsing ' + what)
        dic["timeref"]=int(line[base],16)
        dic["stratum"]=int(line[base+1],16)
        dic['rtc_s'] = 16777216*int(line[base+2],16) + 65536*int(line[base+3],16) + 256*int(line[base+4],16) + int(line[base+5],16)
        dic['rtc_d'] = dic['rtc_s'] / 86400 # day
        dic['rtc_h'] = (dic['rtc_s'] % 86400) # time of day in seconds since midnight
        dic['rtc_ms'] = 256*int(line[base+6],16) + int(line[base+7],16)
        dic['rtc'] = dt.fromtimestamp(dic['rtc_s'] + 0.001*dic['rtc_ms'])
        #dic['rtcs'] = dt.strftime( dt.fromtimestamp(dic['rtc_s'] + 0.001*dic['rtc_ms']), '%Y.%m.%d %H:%M:%S.%f')
        return dic

    def parse_cmd_setcfg(self, dic, line, base):
        """

        """
        return dic

    def parse_msg_rtdbg(self, dic, line, base):
        dic["parent"] = int(line[base],16)
        base += 1
        dic["neighbours"] = int(line[base],16)
        if self.debug>0:
            print("Neighbours = {}".format( dic["neighbours"] ))
        neighbour_size = 5 # 5 B: id, hops, avg_rssi and 2 B for number of messages
        base += 1
        for neighbour in range(dic["neighbours"]):
            neighbour = self.parse_neighbour(line[base:base+neighbour_size])
            dic["node"+str(neighbour["id"])] = neighbour
            base += neighbour_size
        return dic

    def parse_neighbour(self, info):
        """ 2-byte value (num_msg) is in BigEndian """
        n = {}
        n["id"] = int(info[0],16)
        n["hops"] = int(info[1],16)
        n["avg_rssi"] = int(info[2],16) - 256 # signed number!
        n["num_msg"] = 256*int(info[3],16) + int(info[4],16)
        return n

    def clean_results_up(self, d):
        """ clean up the dictionary with results. E.g. remove the sensor data
        that is physically impossible, or packets from nodes that do not exist
        the argument is in dictionary d """
        for k,v in d.iteritems():
            try:
                if k=="temp":
                    if d[k] < -25 or d[k] > 85:
                        d[k] = float('nan')
                elif k=="batt":
                    if d[k] < 1.0 or d[k] > 3.5:
                        d[k] = float('nan')
                elif k=="hum":
                    if d[k] < 0.0 or d[k] > 100.0:
                        d[k] = float('nan')
                elif k=="ir":
                    if d[k] < 0.0 or d[k] > 2000.0:
                        d[k] = float('nan')
                elif k=="photo":
                    if d[k] < 0.0:
                        d[k] = float('nan')
                    #if d[k] > 4096.0:
                #    d[k] = 4096
            except KeyError:
                print("Sth is very wrong with Parser!", file=sys.stderr)
        return d

    def print_packet(self, dic, line, fileout=False, hex_out=False, csv=False):
        """ Print packet in human-readable format """
        if hex_out:
            print(line, end="")
        else:
            try:
                fileout = fileout or sys.stdout
                if csv:
                    format_string = "{}; {}; {}; {}; {}; {}; {};"
                else:
                    format_string = "{}, from={:d}, to={:d}, via={:d}, seq_no={:d}, hops={:d}, rssi={:d},"
                print(format_string.format(
                    dic["ts"],dic["src"],dic["dst"],dic["via"],dic["seq"],dic["hops"],dic["rssi"]), end='', file=fileout)
                # print neighbour info at the end of the packet, so first keep it
                # in a list
                neighbours = []
                for k,v in iter(sorted(dic.items())):
                    if k not in ("ts", "src", "dst", "via", "seq", "rssi",
                            "proto", "node_type", "board_type"):
                        if k in ("ndrift", "bdrift"):
                            print(" {}={:0.4f},".format(k,v),end='', file=fileout)
                        elif type(v) == type(1.1):
                            print(" {}={:0.2f},".format(k,v),end='', file=fileout)
                        # the only dictionaries are neighbouring nodes descriptions
                        # -- print these starting from newlines
                        elif type(v) == type({}):
                            neighbours.append((k,v))
                        else:
                            print(" {}={},".format(k,v),end='', file=fileout)
                            #print(" ", end='', file=fileout)
                for kv in neighbours:
                    k,v = kv[0],kv[1]
                    print("\n\t{}={},".format(k,v),end='', file=fileout)
                print("", file=fileout)
                sys.stdout.flush()
            except KeyError as err:
                try:
                    if dic["msg_type"] == "tinyOS_autoresponse":
                        print("{}, msg_type={}".format(dic["ts"], dic["msg_type"]))
                    else:
                        print('KeyError: ' + str(err), file=sys.stderr)
                        print(dic)
                except KeyError as err:
                    print('KeyError: ' + str(err), file=sys.stderr)
                    print(dic)

    def parse_line(self, line):
        """ parse a hex dump line from NetServ
            header (11B):
                1B proto_ver, 1B msg_type, 2B dst_addr, 2B src_addr, 2B seqNo, 1B txPower,
                1B nodeType, 1B boardType
            payload:
                1B num_data, num_data * {1B id, 2B value}
            packages structures based on WSN/Apps/common/msgheader.h,
            snooppacket.h
            TODO: use XML configuration:
        """
        CRCerror = False
        lineOK = True

        if line[0:1]==' ':
            return {"msg_type":"NetServ_info"}

        try:
            base = self.base
            ll = line.split()

            if len(ll) < 10:
                d = {"msg_type":"tinyOS_autoresponse"}
                try:
                    d["ts"] = datetime.datetime.strptime(' '.join(ll[:2]), '%Y.%m.%d %H:%M:%S.%f')
                    return d
                except ValueError as err:
                    if self.debug>0:
                        print('ValueError:' + str(err))
                        print('--------line----------')
                        print(line)
                    return {"msg_type":"NetServ_info"}
            else:
                d = {}
            d["ts"] = datetime.datetime.strptime(' '.join(ll[:2]), '%Y.%m.%d %H:%M:%S.%f')
            #d["lpl"] = 256*int(ll[base-10],16) + int(ll[base-9],16)
            rssiTmp = int(ll[base-7],16)
            if rssiTmp>127:
                rssiTmp=rssiTmp - 256
            d["rssi"] = rssiTmp-45 # signed 8-b number (-45 is RSSI offset - see CC2420 spec.)
            #d["rssi"] = int(ll[base-7],16) - 255 - 1 # signed 8-b number
            d["lqi"] = int(ll[base-6],16)
            d["proto"] = int(ll[base],16)
            d["via"] = 256*int(ll[base-14],16) + int(ll[base-13],16)

            hdr_end=12  # Justin Case :-)

            d["via"] = 256*int(ll[base-14],16) + int(ll[base-13],16)
            if d["proto"]==0:
                d["check"] = ll[base+9] # . ll[base+10] . ll[base+11] # "aaaaaa"
                d["check2"] = ll[base+11] # . ll[base+10] . ll[base+11] # "aaaaaa"
                d["nstamp"] = (256*int(ll[base+12],16) + int(ll[base+13],16))*65536 + 256*int(ll[base+14],16) + int(ll[base+15],16)
                d["bstamp"] = (256*int(ll[base-5],16) + int(ll[base-4],16))*65536 + 256*int(ll[base-3],16) + int(ll[base-2],16)
                d["msg_type"] = self.msg_types['MSG_DRIFT']
                d["dst"] = 256*int(ll[base-16],16) + int(ll[base-15],16)
                d["src"] = 256*int(ll[base+2],16) + int(ll[base+3],16)
                d["seq"] = 256*int(ll[base+4],16) + int(ll[base+5],16)
                d["hops"] = 1
            else:
                d["msg_type"] = int(ll[base+1],16)
                d["dst"] = 256*int(ll[base+2],16) + int(ll[base+3],16)
                d["src"] = 256*int(ll[base+4],16) + int(ll[base+5],16)
                d["seq"] = 256*int(ll[base+6],16) + int(ll[base+7],16)

                if d["proto"]==1:
                    d["hops"] = int(ll[base+8],16)
                    d["txP"] = int(ll[base+9],16)
                    d["node_type"] = int(ll[base+10],16)
                    d["board_type"] = int(ll[base+11],16)
                    hdr_end=12

                if d["proto"]==2:
                    d["node_type"] = int(ll[base+8],16)
                    d["board_type"] = int(ll[base+9],16)
                    d["hops"] = int(ll[base+10],16)
                    d["txP"] = int(ll[base+11],16)
                    d["crchdr"] = 256*int(ll[base+12],16) + int(ll[base+13],16)
                    hdr_end=14

            # look for CRC errors
            m = re.search('CRC ....', line)
            if m:
                d["crc"] = m.group(0)[-4:]
                return {}


            # the header stops here - now parse payload depending on the msg_type
            if d["msg_type"] == self.msg_types['MSG_DATA']:
                d = self.parse_msg_data(d,ll,base+hdr_end)
            elif d["msg_type"] == self.msg_types['MSG_RESET']:
                d = self.parse_msg_reset(d,ll, base+hdr_end)
            elif d["msg_type"] == self.msg_types['MSG_HELLO']:
                d = self.parse_msg_hello(d,ll, base+hdr_end)
            elif d["msg_type"] == self.msg_types['MSG_EHLO']:
                d = self.parse_msg_ehlo(d,ll, base+hdr_end)
            elif d["msg_type"] == self.msg_types['MSG_RTDBG']:
                d = self.parse_msg_rtdbg(d,ll, base+hdr_end)
            elif d["msg_type"] == self.msg_types['CMD_RTDBG']:
                d = self.parse_cmd_rtdbg(d,ll, base+hdr_end)
            elif d["msg_type"] == self.msg_types['MSG_TIMESTAMP']:
                d = self.parse_msg_timestamp(d,ll, base+hdr_end)
            elif d["msg_type"] == self.msg_types['MSG_SETTIME']:
                d = self.parse_setgettime(d,ll, base+hdr_end, 'MSG_SETTIME')
            elif d["msg_type"] == self.msg_types['MSG_GETTIME']:
                d = self.parse_setgettime(d,ll, base+hdr_end, 'MSG_GETTIME')
            elif d["msg_type"] == self.msg_types['CMD_SETCFG']:
                d = self.parse_cmd_setcfg(d,ll,base+hdr_end)
            elif d["msg_type"] == self.msg_types['MSG_DRIFT']:
                d = self.parse_drift(d,ll,base+hdr_end)

            else:
                print('msg_type not handled: {}'.format(d["msg_type"]))
                d = self.parse_unknown(d,ll,base+hdr_end, d["msg_type"])
                return d;


        except IndexError as err:
            if self.debug>0:
                print('IndexError: hexdump line probably too small', file=sys.stderr)
                print(err, file=sys.stderr)
                print(d, file=sys.stderr)
                print(line, file=sys.stderr)
                print(len(line), file=sys.stderr)
            d["msg_type"] = "TYPE_UNKNOWN"
        except ValueError as err:
            print('ValueError: problem with packet structure, probably CRC error', file=sys.stderr)
            print(err, file=sys.stderr)
            d["msg_type"] = "TYPE_UNKNOWN"
            
        if self.clean:
            d = self.clean_results_up(d)
            
        # filter out unwanted messages
        if len(self.nodes) > 0:
            if int(d["src"]) not in self.nodes:
                raise Error("Wrong node number: {}".format(d["src"]))
            if int(d["src"]) >255:
                raise Error("Invalid source number: {}".format(d["src"]))
        if len(self.via) > 0:
            if int(d["via"]) not in self.via:
                raise Error("Wrong node number: {}".format(d["via"]))
        if len(self.dates) > 0:
            if d["ts"] < self.dates[0] or d["ts"] > self.dates[1]:
                raise Error("Wrong date: {}".format(d["ts"]))
                lineOK=False
        
        # Respond to errors
        if self.debug>0:
            if not lineOK:
                print("  --- Incorrect line  ----")
                print(ll)
                print("{} from={} to={} via={} seq_no={} hops={} rssi={}".format(
                    d["ts"],d["src"],d["dst"],d["via"],d["seq"],d["hops"],d["rssi"]))
                print("  ------------------------ ")
            if CRCerror:
                print("  --- CRC error  ----")
                print(ll)
                print("{} from={} to={} via={} seq_no={} hops={} rssi={}".format(
                        d["ts"],d["src"],d["dst"],d["via"],d["seq"],d["hops"],d["rssi"]))
                print("  ------------------------ ")
        return d

class ParserXML(Parser):
    def __init__(self, xml_file = False):
        self.prot_xml_file = xml_file or '../generator/input/packet-wsn_zak.xml'
        self.packet_base  = 28 
        self.packet_struct = {'header':[], 'sensors':{}}

        try:
        # parse XML protocol description and save it in self.packet_struct
            with open(self.prot_xml_file) as xml:
                tree = ET.parse(self.prot_xml_file)
                root = tree.getroot()
                field_size = {'uint8':1, 'uint16':2}
                idx  = 0    # temporary shift from base to navigate in the packet
                    # get header fields, the last 3 are a description of sensors
                    # 'short' attribute is mandatory for each field in packet header
                for f in root.findall(".//field")[:-3]:
                    #print f.tag, f.attrib
                    fsize = field_size[f.attrib['type']]
                    idx = idx + fsize
                    try:
                        short = f.attrib['short']
                    except KeyError as err:
                        print("Parser.ParserXML: short attribute is mandatory for header files!")
                        print("check file: " + self.prot_xml_file)
                        print(f.attrib)
                        raise KeyError 
                    f.attrib['idx']=idx;
                    f.attrib['fsize']=fsize
                    self.packet_struct['header'].append(f.attrib)
                    #for c in root.findall()
                    # get sensor types
                for c in root.findall(".//field/[@id='wsn.sensortype']/switch/case"):
                    # use text between tags if no short name is provided
                    try:
                        short = c.attrib['short']
                    except KeyError as err:
                        short = c.text
                    # if there is no formula in XML, then formula should be 'v'
                    try:
                        formula = c.attrib['formula']
                    except KeyError as err:
                        c.attrib['formula'] = 'v' 
                    self.packet_struct['sensors'][int(c.attrib['equals'],16)]=c.attrib
        except IOError as err:
            print('I can not find the default or specified XML file', file=sys.stderr)
                
    def showProtocol(self):
        pprint.pprint(self.packet_struct)

    def get_value(self, ll, base, endian, size):
        """ calculate value from hex form divided into bytes
        ll is a list of bytes """
        if size > 1:
            if endian == 'BIG_ENDIAN':
                hexval = ''.join([x for x in ll[base:base+size]])
            else:
                hexval = ''.join([x for x in reversed(ll[base:base+size])])
        else:
            hexval = ll[base]
        return int(hexval,16)


    def parse_line(self, line):
        print(line)
        dic = {}
        base = self.packet_base
        ll = line.split()

        # self.packet_struct['header'] is a list of header fields with sizes 1-2B
        for field in self.packet_struct['header']:
            dic[field['short']] = self.get_value(ll, base, field['encoding'], field['fsize'])
            base = base + field['fsize']
            print("base = {}, fiel = {}, val = {}".format(base, field['short'],
                dic[field['short']]))
        
        # self.packet_struct['sensors'] is a dict with integer keys equal to 
        # equals attribute in the XML specification of the protocol
        for sensor in range(dic['sensors']):
            sensor_id = int(ll[base],16)
            v = self.get_value(ll, base+1, 'BIG_ENDIAN', 2)
            # print('formula = {}'.format(self.packet_struct['sensors'][sensor_id]['formula']))
            code =  parser.expr(self.packet_struct['sensors'][sensor_id]['formula']).compile()
            # print('type = {}'.format(type(code)))
            sensor_value = eval(code)
            short = self.packet_struct['sensors'][sensor_id]['short']
            print("base = {}, id = {}, val = {}, short={}".format(base, sensor_id, sensor_value,
                short))
            dic[short] = sensor_value
            base = base + 3

        return dic

class Error(Exception):
    def __init__(self, msg):
        self.msg = msg

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

def usage():
    usage_text = """
    usage: cat logfile | ./Parser.py [options]
    -t      --dates      -- from,to date: Y/m/d,Y/m/d
    -o      --nodes      -- a comma-separated list of SOURCE node numbers: e.g. 12,13,14
    -v      --via        -- a comma-separated list of LAST HOP TRANSMITTERs node numbers: e.g. 12,13,14
    -h      --help       -- print this message
    -d      --debug      -- operate in debug mode -- print more info 
    -f      --filein     -- file to read the data from 
    -g      --fileout    -- file to write data to
    -u      --unique     -- only use each message once
    -x      --hex        -- print filtered messages in hex form
    -X      --protocol-xml -- XML file with protocol description 
    -C      --csv        -- print results in CSV format [TO BE IMPLEMENTED]
    -s      --stat       -- print statistics in a table
    """
    print(usage_text, file=sys.stderr)


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "Cdf:g:ho:st:uv:X:x",
                    ["csv","via","fileout","filein", "dates", "nodes", "protocol-xml", "debug",
                        "help", "unique", "hex", "stat"])
        except getopt.error as msg:
             raise Usage(msg)
        filein = False
        fileout= False
        csvformat= False
        stat= False
		

        p = Parser()
        for o, a in opts:
            if o in ("-h", "--help"):
                raise Usage("help")
                sys.exit()
            elif o in ("-u", "--unique"):
                p.unique = True
            elif o in ("-x", "--hex"):
                p.hex = True
            ## xml-header is a temporary option for protocol description file ###
            elif o in ("-X", "--protocol-xml"):
                pxml = ParserXML(a)
            elif o in ("-s", "--stat"):
                s = Stat()
                stat = True
            elif o in ("-C", "--csv"):
                csvformat = True
            elif o in ("-o", "--nodes"):
                if stat:
                    for x in a.split(','):
                        s.nodes_list.append(int(x))
                        s.nodes[int(x)]=int(x)
                else:
                    p.nodes = [int(x) for x in a.split(',')]
            elif o in ("-v", "--via"):
                p.via = [int(x) for x in a.split(',')]
            elif o in ("-f", "--filein"):
                try:
                    filein = open(a)
                except Error as err:
                    filein = False
                    if p.debug>0:
                        print(err.msg, file=sys.stderr)
            elif o in ("-g", "--fileout"):
                try:
                    fileout = open(a,'w')
                except Error as err:
                    fileout = False
                    if p.debug>0:
                        print(err.msg, file=sys.stderr)
                        return 2
            elif o in ("-t", "--dates"):
                p.dates = [datetime.datetime.strptime(x, '%Y/%m/%d') for x in a.split(',')]
                print(p.dates[0])
                print(p.dates[1])
            elif o in ("-d", "--debug"):
                p.debug = p.debug+1;
        #pxml.showProtocol()
        while True:
            if filein:
                line = filein.readline()
                if (p.debug>1):
                    print(line)
            else:
                line = sys.stdin.readline()
                if (p.debug>1):
                    print(line)
            if len(line) == 0:
                raise Error("No input line")
            try:
                dic = p.parse_line(line)
                #print("---------------------")
                #print(pxml.parse_line(line))
                #print("---------------------")
            except Error as err:
                if p.debug>0:
                    print(err.msg, file=sys.stderr)
                continue
            if dic=={}:
                continue
            if p.debug>0:
                print(dic, file=sys.stderr)
            uniq=p.new_pkg(dic)
            if (p.unique and uniq) or not p.unique:
                if stat:
                    s.add(dic, uniq)
                    s.print()
                    continue
                if p.hex:
                    print(line, end="")
                else:
                    # def print_packet(self, dic, line, fileout=False, hex_out=False, csv=False):
                    p.print_packet(dic, line, fileout=fileout, hex_out=p.hex, csv=csvformat)

    except Error as err:
        print(err.msg, file=sys.stderr)
        print("Expected error", file=sys.stderr)
        if filein:
            filein.close()
        return 1
    except Usage as err:
        print(err.msg, file=sys.stderr)
        print("for help use --help", file=sys.stderr)
        print("use -u or --unique to print each packet only once", file=sys.stderr)
        usage()
        return 2

if __name__ == "__main__":
    sys.exit(main())
