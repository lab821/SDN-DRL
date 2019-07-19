#!/bin/bash

# add flow with setting queue
# sudo ovs-ofctl add-flow s1 ip,nw_src=10.0.0.2,actions=set_queue:0,normal
# sudo ovs-ofctl add-flow s1 ip,nw_src=10.0.0.3,actions=set_queue:0,normal

# add flow with meter
sudo ovs-ofctl -O OpenFlow13 add-meter s1 meter=5,kbps,stats,burst,band=type=drop,rate=100,burst_size=10
sudo ovs-ofctl -O OpenFlow13 add-flow s1 ip,nw_src=10.0.0.1,actions=meter:5,output:2
sudo ovs-ofctl -O OpenFlow13 add-flow s1 ip,nw_src=10.0.0.2,actions=meter:5,output:1
# sudo ovs-ofctl -O OpenFlow13 add-flow s1 in_port=1,actions=meter:5,output:2
# sudo ovs-ofctl -O OpenFlow13 add-flow s1 in_port=2,actions=meter:5,output:1
