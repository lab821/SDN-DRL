#!/bin/bash

# sudo ovs-vsctl set port s1-eth1 qos=@newqos -- --id=@newqos create qos type=linux-htb queues=0=@q0,1=@q1,2=@q2,3=@q3 -- --id=@q0 create queue other-config:max-rate=1000000 -- --id=@q1 create queue other-config:max-rate=1000000 -- --id=@q2 create queue other-config:max-rate=1000000 -- --id=@q3 create queue other-config:max-rate=1000000 
sudo ovs-vsctl set port s1-eth1 qos=@newqos -- --id=@newqos create qos type=linux-htb queues=0=@q0,1=@q1 -- --id=@q0 create queue other-config:max-rate=1000000000 -- --id=@q1 create queue other-config:max-rate=100000000 
