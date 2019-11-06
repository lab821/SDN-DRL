#!/bin/bash
sudo ovs-vsctl -- --all destroy qos -- --all destroy queue

sudo ovs-vsctl set port s1-eth1 qos=@newqos -- --id=@newqos create qos type=linux-htb other-config:max-rate=100000000 queues=0=@q0,1=@q1 -- --id=@q0 create queue other-config:priority=0 -- --id=@q1 create queue other-config:priority=1
sudo ovs-vsctl set port s1-eth2 qos=@newqos -- --id=@newqos create qos type=linux-htb other-config:max-rate=100000000 queues=0=@q0,1=@q1 -- --id=@q0 create queue other-config:priority=0 -- --id=@q1 create queue other-config:priority=1
sudo ovs-vsctl set port s1-eth3 qos=@newqos -- --id=@newqos create qos type=linux-htb other-config:max-rate=100000000 queues=0=@q0,1=@q1 -- --id=@q0 create queue other-config:priority=0 -- --id=@q1 create queue other-config:priority=1
sudo ovs-vsctl set port s1-eth4 qos=@newqos -- --id=@newqos create qos type=linux-htb other-config:max-rate=100000000 queues=0=@q0,1=@q1 -- --id=@q0 create queue other-config:priority=0 -- --id=@q1 create queue other-config:priority=1