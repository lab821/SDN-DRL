#!/bin/bash

case $1 in
	udp)
		;;
	tcp)
		iperf3 -c 10.0.0.1 -t 600 -B 10.0.0.2 --cport 12345
	;;
	*)
		iperf3 -c 10.0.0.1 -t 600 -B 10.0.0.2 --cport 12345
	;;
esac
