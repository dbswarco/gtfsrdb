#!/usr/bin/python

import urllib.request, json

try:
    url = "https://api.wmata.com/gtfs/bus-gtfsrt-tripupdates.pb"

    hdr ={
    # Request headers
    'Cache-Control': 'no-cache',
    }

    req = urllib.request.Request(url, headers=hdr)

    req.get_method = lambda: 'GET'
    response = urllib.request.urlopen(req)
    print(response.getcode())
    print(response.read())
except Exception as e:
    print(e)
