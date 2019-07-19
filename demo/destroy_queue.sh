#!/bin/bash

sudo ovs-vsctl -- --all destroy qos -- --all destroy queue
sudo ovs-vsctl list qos
sudo ovs-vsctl list queue
