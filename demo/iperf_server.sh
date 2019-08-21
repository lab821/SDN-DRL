#!/bin/bash

case $1 in
	udp)
		;;
	*)
		iperf3 -s -i 2 &
		iperf3 -s -i 2 -p 5202 &
		iperf3 -s -i 2 -p 5203
	;;
esac
