#!/bin/bash

case $1 in
	udp)
		;;
	tcp)
		iperf -s -i 2
	;;
	*)
		iperf -s -i 2
	;;
esac