#!/bin/bash

curl -X POST -d '{
    "dpid": 1,
    "cookie": 0,
    "table_id": 0,
    "idle_timeout": 0,
    "hard_timeout": 0,
    "priority": 1,
    "flags": 0,
    "match":{
        "dl_type": 2048,
        "nw_proto": 6,
        "tp_dst": 5001,
        "tp_src": 35992,
        "nw_dst": "10.0.0.2",
        "nw_src": "10.0.0.1"
    },
    "actions":[
        {
            "type":"OUTPUT",
            "port": 1
        }
    ]
 }' http://localhost:8080/stats/flowentry/modify_strict