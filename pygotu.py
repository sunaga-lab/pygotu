#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import sys, os, time
import serial
import datetime, time
from struct import pack, unpack


devname = '/dev/ttyACM0'

def ord_u(ch):
    if isinstance(ch, str):
        return ord(ch)
    else:
        return ch

def chr_u(i):
    return bytes([i])

def hexdumps(s):
    return " ".join("{:02X}".format(ord_u(ch)) for ch in s)



class GTDev:
    def __init__(self, devname, debug = False):
        self.devname = devname
        self.dev = serial.Serial(devname, 9600)
        self.dev.flush()
        self.debug = debug

    def write_cmd(self, cmd1, cmd2):
        assert len(cmd1) == 8
        assert len(cmd2) == 8
        assert isinstance(cmd1, bytes)
        assert isinstance(cmd2, bytes)
        cs = 0
        for ch in cmd1 + cmd2[:7]:
            cs += ord(ch) if isinstance(ch, str) else ch
        cs = cs & 0xff
        cs = ((cs^0xff) + 0x01) & 0xff
        if isinstance(cmd2, str):
            cmd2 = cmd2[:7] + chr(cs)
        else:
            cmd2 = cmd2[:7] + bytes([cs])
            print("CMS2:", cmd2, " bcs:", bytes([cs]))
        if self.debug:
            print("CMS2 = ", cmd2)
            print("CS = ", cs)
            print("APPENDED = ", cmd1 + cmd2)
            print("Send1&2: ", hexdumps(cmd1 + cmd2))
        self.dev.write(cmd1 + cmd2)
        #print("Send2: ", hexdumps()cmd2)
        #self.dev.write(cmd2)

    def read(self, sz):
        result = self.dev.read(sz)
        if self.debug:
            print("Read: ", hexdumps(result))
        return result

    def read_resp(self, fmt = None):
        recv = self.read(3)
        print("Receuved: ", recv, " and[0]:", recv[0])
        if recv[0] != "\x93" and recv[0] != 0x93:
            raise Exception()
        m, sz = unpack(">ch", recv)
        if sz < 0:
            if self.debug:
                print("Read Error:", sz)
            raise Exception("Read Error")
        if self.debug:
            print("Reading", sz, "bytes...")

        resp = self.read(sz)
        if fmt:
            print("resp:", resp, "sz:",sz)
            return unpack(">" + fmt, resp)
        else:
            return resp


    def nmea_switch(self, mode):
        mch = ["\x00", "\x01", "\x02", "\x03"][mode]
        self.write_cmd(
            b"\x93\x01\x01" + mch + b"\x00\x00\x00\x00",
            b"\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        self.read(1)

    def identify(self):
        self.write_cmd(
            b"\x93\x0a\x00\x00\x00\x00\x00\x00",
            b"\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        serial, v_maj, v_min, model, v_lib = self.read_resp(fmt = "IbbHH")
        if self.debug:
            print("Serial:", serial)
            print("Ver:", v_maj, v_min)
            print("Model:", model)
            print("USBlib:", v_lib)

    def count(self):
        self.write_cmd(
            b"\x93\x0b\x03\x00\x1d\x00\x00\x00",
            b"\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        n1, n2 = self.read_resp(fmt = "Hb")
        num = n1*256 + n2
        if self.debug:
            print("Num DP:", num, "(", n1, n2, ")")
        return num

    def flash_read(self, pos = 0, size = 0x1000):
        chpos = pack(">I", pos)     
        chsz = pack(">H", size) 
        print("CH2: ", chpos[2:3] + b"\x00\x00\x00\x00\x00\x00")
        self.write_cmd(
            b"\x93\x05\x07" + chsz + b"\x04\x03" + chr_u(chpos[1]),
            chpos[2:4] + b"\x00\x00\x00\x00\x00\x00"
        )
        buf = self.read_resp()
        return buf
    
    def purge_all_120(self):
        purge_flag = False
        n_blocks = 0x700
        
        for i in range(n_blocks, 0, -1):
            print("I=", i)
            if purge_flag:
                while self.unk_write2(0x01) != chr(0x00):
                    pass
            else:
                if self.flash_read(pos = (i * 0x1000), size = 0x10) != ("\xff" * 0x10):
                    purge_flag = True
                else:
                    continue
            self.unk_write1(0)
            self.flash_write_purge(i * 0x1000)
        if purge_flag:
            self.unk_purge1(0x1e)
            self.unk_purge1(0x1f)
            while self.unk_write2(0x01) != chr(0x00):
                pass
        self.unk_purge1(0x1e)
        self.unk_purge1(0x1f)


    def purge_all_gt900(self):
        purge_flag = False
        n_blocks = 0x700
        
        for i in range(n_blocks-1, 0, -1):
            print("I=", i)
            if not purge_flag:
                print("NP")
                if self.flash_read(pos = (i * 0x1000), size = 0x10) != ("\xff" * 0x10):
                    print("pf = true")
                    purge_flag = True
                else:
                    print("cont.")
                    continue
            print("Writing")
            self.unk_write1(0x00)
            self.flash_write_purge(i * 0x1000)
            print("UNKW2")
            while self.unk_write2(0x01) != chr(0x00):
                print("Waiting...")
            print("Purged.")


    def flash_write_purge(self, pos):
        chpos = pack(">I", pos)
        w = 0x20
        self.write_cmd(
            b"\x93\x06\x07\x00\x00\x04" + chr_u(w) + chpos[1],
            chpos[2] + chpos[3] + b"\x00\x00\x00\x00\x00\x00"
        )
        buf = self.read_resp()
        return buf
    
    def unk_write1(self, p1):
        self.write_cmd(
            b"\x93\x06\x04\x00" + chr_u(p1) + b"\x01\x06\x00",
            b"\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        buf = self.read_resp()
        return buf

    def unk_write2(self, p1):
        p1ch = pack('>H', p1)
        self.write_cmd(
            b"\x93\x05\x04" + p1ch + b"\x01\x05\x00",
            b"\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        buf = self.read_resp()
        return buf

    def unk_purge1(self, p1):
        self.write_cmd(
            b"\x93\x0C\x00" + chr_u(p1) + b"\x00\x00\x00\x00",
            b"\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        buf = self.read_resp()
        return buf

    def unk_purge2(self, p1):
        self.write_cmd(
            b"\x93\x08\x02" + chr_u(p1) + b"\x00\x00\x00\x00",
            b"\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        buf = self.read_resp()
        return buf

    def all_records(self):
        rpos = 0
        buf = ""
        num_rec_read = 0
        num_rec_all = self.count()
    
        RECSIZE = 0x20
        while True:
            rpos += 1
            buf = self.flash_read(rpos * 0x1000)
            for i in range(len(buf) // RECSIZE):
                yield GTRecord(num_rec_read, buf[i*RECSIZE:(i+1)*RECSIZE])
                num_rec_read += 1
                if num_rec_read >= num_rec_all:
                    if self.debug: print("End by count:", num_rec_all)
                    return
            if self.debug: print("End RECLOOP")

    def all_tracks(self):
        idx = 0
        curlist = []
        for rec in self.all_records():
            if rec.kind == 'WP':
                curlist.append(rec)
            if rec.kind == 'LOG' and rec.msg == 'RESET COUNTER':
                if curlist:
                    yield GTTrack(idx, curlist)
                    idx += 1
                    curlist = []
        if curlist:
            yield GTTrack(idx, curlist)


class GTTrack:
    def __init__(self, idx, reclist):
        self.idx = idx
        self.records = list(reclist)

    @property
    def first_point(self):
        return self.records[0]

    @property
    def last_point(self):
        return self.records[len(self.records) - 1]
    
    @property
    def first_time(self):
        return self.first_point.localtime

    @property
    def last_time(self):
        return self.last_point.localtime

    @property
    def num_points(self):
        return len(self.records)
    
    def __str__(self):
        return "{0.idx}: {0.first_time:%Y/%m/%d %H:%M:%S} - {0.last_time:%Y/%m/%d %H:%M:%S} points:[{0.num_points}]".format(self)

class GTRecord:
    def __init__(self, idx, s):
        self.valid = True
        self.idx = idx
        self.s = s
        flag, ym, dhm, ms = unpack(">BBHH", self.s[0x00:0x06])
        self.plr = unpack(">H", self.s[0x1e:0x20])
        self.flag = flag
        self.year = (ym >> 4) + 2000
        self.month = (ym & 0x0F) % 13
        self.day = dhm >> 11
        if self.day <= 0:
            self.day = 1
        self.hour = ((dhm >> 6) & 0b00011111) %24
        self.minutes = (dhm & 0b00111111) % 60
        self.sec = int(ms / 1000) % 60
        self.ms = ms % 1000

        try:
            self.datetime = datetime.datetime(self.year, self.month, self.day, self.hour, self.minutes, self.sec, self.ms)
        except ValueError:
            self.datetime = None
            self.valid = False
            print("InvalidDate:", (self.year, self.month, self.day, self.hour, self.minutes, self.sec, self.ms))
            
        self.msg = ""

        if flag == 0xF1:
            self.parse_device_log()
        elif flag == 0xF5:
            self.parse_heartbeat()
        else:
            self.parse_waypoint()

    @property
    def localtime(self):
        return self.datetime - datetime.timedelta(seconds = time.timezone)
    
    def parse_waypoint(self):
        self.kind = "WP"
        (ae, self.r_ele_p, self.r_lat, self.r_lon, self.r_ele_gps, self.r_speed, self.r_course, self.f2) = unpack(">HiiiiHHH", self.s[0x06:0x1e])
        
        self.unk1 = (ae >> 12)
        self.ehpe = (ae & 0b0000111111111111) / 10.0 # in m

        self.lon = self.r_lon / 10000000.0 # 
        self.lat = self.r_lat / 10000000.0 #
        if abs(self.lat) > 180:
            print("lat:", self.lat)
            print("lon:", self.lon)
            print("r_lat:", self.r_lat)
            raise Exception("Invalid lat")
        self.ele = self.r_ele_p / 100.0 # in m
        self.ele_gps = self.r_ele_gps / 100.0 # in m
        self.speed = (self.r_speed / 100.0) / 1000.0 * 3600.0 # km/h
        self.course = self.r_course / 100.0 # degree
        self.sat = self.f2 & 0b00001111 # num of sat
        
        
        self.flagopts = set()
        
        FLAGNAMES = ["U0", "U1", "WP", "U3", "NDI", "TSTOP", "TSTART", "U7"]
        for bit in range(8):
            if self.flag & (1 << bit):
                self.flagopts.add(FLAGNAMES[bit])
        
        self.fopts = ",".join(self.flagopts)
        
        self.desc = "WP LATLON:({0.lat}, {0.lon}) ele:{0.ele} speed:{0.speed} uf={0.unk1:b},{0.f2:b} ehpe={0.ehpe} {0.fopts}".format(self)


    def parse_device_log(self):
        self.kind = "LOG"
        self.msg = self.s[0x06:0x1e].decode('UTF-8').replace('\x00', '').strip()
        self.desc = "LOG {0.msg}".format(self)

    def parse_unknown(self):
        self.kind = "UNK"
        self.desc = "UNK {0.flag}".format(self)

    def __str__(self):
        return "{0.datetime:%Y/%m/%d %H:%M:%S} {0.desc}".format(self)

def test():
    dev = GTDev(devname, debug = True)

    dev.identify()
    n = dev.count()
 
    #for track in dev.all_tracks():
    #    print(track)

    for rec in dev.all_records():
        print("- ", rec.idx, "/", n, ":", rec)

def main():
    test()

if __name__ == '__main__':
    main()

