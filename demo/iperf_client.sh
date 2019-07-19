#!/bin/bash

case $1 in
	udp)
		;;
	tcp)
		iperf -c 10.0.0.1 -t 600
	;;
	*)
		iperf -c 10.0.0.1 -t 600
	;;
esac