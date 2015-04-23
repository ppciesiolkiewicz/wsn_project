#!/usr/bin/python
# -*- coding: utf-8 -*-

import MySQLdb as mdb
import sys
import ConfigParser
import socket
import pprint
import time

from Parser import Parser


class Database():

    def __init__(self, configFile = 'settings.ini'):
        config = ConfigParser.RawConfigParser()
        config.read(configFile)
        host = config.get('database', 'host')
        user = config.get('database', 'user')
        password = config.get('database', 'password')
        database = config.get('database', 'database')

        try:
            self._db_connection = mdb.connect(host, user, password, database);
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0],e.args[1])
            sys.exit(1)

        print("Connected to database {0} - {1}".format(host, database))

    def __del__(self):
        if self._db_connection:
            self._db_connection.close()

    def addMeasurement(self, measurementDict):
            measurementDict['debug2_1'] = measurementDict['debug2'][0]
            measurementDict['debug2_2'] = measurementDict['debug2'][1]
            measurementDict['debug2_3'] = measurementDict['debug2'][2]
            measurementDict['debug2_4'] = measurementDict['debug2'][3]
            measurementDict['debug2_5'] = measurementDict['debug2'][4]

            query = ("INSERT INTO measurement "
                    "(`timestamp`, `from`, `to`, `seq_no`, `hops`, `batt`,"
                    "`debug2_1`, `debug2_2`, `debug2_3`, `debug2_4`, `debug2_5`,"
                    "`hum`, `msg_type`, `photo`, `temp`) "
                    "VALUES (%(ts)s,%(src)s,%(dst)s,%(seq)s,%(hops)s,%(batt)s,"
                    "%(debug2_1)s,%(debug2_2)s,%(debug2_3)s,%(debug2_4)s,%(debug2_5)s,"
                    "%(hum)s,%(msg_type)s,%(photo)s,%(temp)s)")

            cur = self._db_connection.cursor()
            cur.execute(query, measurementDict)

            self._db_connection.commit()

class Netcat():
    def __init__(self, configFile='settings.ini'):
        config = ConfigParser.RawConfigParser()
        config.read(configFile)
        host = config.get('wsn', 'host')
        port = config.getint('wsn', 'port')
        parser = Parser()
        self.sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sck.connect((host, port))
        print("Connected on {0}:{1}".format(host, port))

    def readLastLine(self):
        data = self.sck.recv(1024)
        return data.strip().split("\n")[-1]

    def __del__(self):
        print("Connection closed.")
        self.sck.shutdown(socket.SHUT_WR)
        self.sck.close()


def main():
    db = Database()
    nc = Netcat()
    p = Parser()
    while True:
        line = nc.readLastLine()
        d = p.parse_line(line)
        if d['msg_type'] != "UKNOWN":
            pprint.pprint(d)
            db.addMeasurement(d)
            time.sleep(10)


if __name__ == "__main__":
    main()

