#!/bin/bash

curl -X POST -d '{
    "dpid":1,
    "table_id":0,
    "priority":2,
    "match":{
        "ipv4_src":"10.0.0.1",
        "eth_type":2048
    },
    "actions":[
        {
            "type":"METER",
            "meter_id": 1
        },
        {
            "type":"OUTPUT",
            "port":2
        }
    ]
}' http://localhost:8080/stats/flowentry/add

curl -X POST -d '{
    "dpid":1,
    "table_id":0,
    "priority":2,
    "match":{
        "ipv4_src":"10.0.0.2",
        "eth_type":2048
    },
    "actions":[
        {
            "type":"METER",
            "meter_id": 1
        },
        {
            "type":"OUTPUT",
            "port":1
        }
    ]
}' http://localhost:8080/stats/flowentry/add