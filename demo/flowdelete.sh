#!/bin/bash

curl -X POST -d '{
    "dpid":1,
    "table_id":0,
    "match":{"tp_src": 56704, "nw_src": "10.0.0.2", "tp_dst": 5201, "nw_dst": "10.0.0.1", "nw_proto": 6, "dl_type": 2048}
}' http://localhost:8080/stats/flowentry/delete