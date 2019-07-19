#!/bin/bash

# param="--link tc,bw=100 "
param=""
for arg in $*
do
	case $arg in
		sflow)
			param=${param}"--custom /opt/sflow-rt/extras/sflow.py "
		;;
		tree)
			param=${param}"--topo tree,depth=2,fanout=2 "
		;;
		single)
			param=${param}"--topo single,4 "
		;;
		r)
			param=${param}"--controller=remote "
		;;
		debug)
			param=${param}"--verbosity=debug "
		;;
		*)
		;;
	esac
done
echo ${param}
sudo mn ${param}
