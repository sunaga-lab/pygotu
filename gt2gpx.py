#!/usr/bin/env python

import pygotu
import sys
import os, os.path



def main():
    if len(sys.argv) < 3:
        print "gt2gpx.py dev dir"
        sys.exit(1)
    
    dev = sys.argv[1]
    destdir = sys.argv[2]
    
    if not os.path.isdir(destdir):
        print "Dest", destdir, "is not directory."
        sys.exit(2)

    dev = pygotu.GTDev(dev, debug = False)

    dev.identify()

    for track in dev.all_tracks():
        print "Importing:", track
        trackname = "Track {0.first_time:%Y/%m/%d %H:%M:%S}".format(track)
        fn = "gt-{0.first_time:%Y-%m-%dT%H-%M-%S}.gpx".format(track)
        with open(os.path.join(destdir, fn), "w") as f:
            f.write("""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" xmlns:pygotu="http://www.sunaga-lab.net/pygotu" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" creator="pygotu" version="1.1" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
  <trk>
    <name>{trackname}</name>
    <desc>pygotu imported track</desc>
    <trkseg>
""".format(trackname = trackname))
            
            for rec in track.records:
                data = """      <trkpt lat="{0.lat}" lon="{0.lon}">
        <ele>{0.ele}</ele>
        <time>{0.datetime:%Y-%m-%dT%H:%M:%SZ}</time>
        <sat>{0.sat}</sat>
        <desc>posdesc</desc>
        <extensions>
          <pygotu:course>{0.course}</pygotu:course>
          <pygotu:speed>{0.speed}</pygotu:speed>
          <pygotu:ehpe>{0.ehpe}</pygotu:ehpe>
          <pygotu:elegps>{0.ele_gps}</pygotu:elegps>
        </extensions>
      </trkpt>
""".format(rec)
                f.write(data)

            f.write("    </trkseg>\n  </trk>\n</gpx>")





if __name__ == '__main__':
    main()

