#!/bin/bash

curl -X POST -d '{
    "dpid": 1,
    "flags": "KBPS",
    "meter_id": 10,
    "bands": [
        {
            "type": "DROP",
            "rate": 10000
        }
    ]
 }' http://localhost:8080/stats/meterentry/add
