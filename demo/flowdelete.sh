#!/bin/bash

curl -X POST -d '{
    "dpid":1,
    "table_id":0,
    "priority":2,
    "actions":[
        {
            "type":"OUTPUT",
            "port":2
        }
    ]
}' http://localhost:8080/stats/flowentry/delete