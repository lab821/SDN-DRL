#!/bin/bash

# for iface in $*
# do
#     # set the rate of ingress, with Kbps
#     sudo ovs-vsctl set interface $iface ingress_policing_rate=10000
#     # set rate beyond rate with Kbps, usually set to 10% of policing_rate
#     sudo ovs-vsctl set interface $iface ingress_policing_burst=2000
#     # show details of interface
#     sudo ovs-vsctl list interface $iface
# done
s=1
eth=0
rate=0
burst=0
a=0
while getopts ":s:e:r:b:ah" arg
do
    case $arg in
        s)
            s=$OPTARG
            ;;
        e)
            eth=$OPTARG
            ;;
        r)
            rate=$OPTARG
            ;;
        b)
            burst=$OPTARG
            ;;
        a)
            a=1
            ;;
        h)
            echo "Options: s|e|r|b|a"
            exit
            ;;
        ?)
            echo "Unknow Argument! Options: s|e|r|b|a"
            ;;
    esac
done

if [ $a -eq 1 ]
then
    for n in $(seq 1 $eth)
    do
        echo "sudo ovs-vsctl set interface s${s}-eth${n} ingress_policing_rate=${rate}"
        echo "sudo ovs-vsctl set interface s${s}-eth${n} ingress_policing_burst=${burst}"
    done
else
    echo "sudo ovs-vsctl set interface s${s}-eth${eth} ingress_policing_rate=${rate}"
    echo "sudo ovs-vsctl set interface s${s}-eth${eth} ingress_policing_burst=${burst}"
fi
read -n 2 -p "Execute these commands?[y/n](default:y)" answer
case $answer in
    y)
        if [ $a -eq 1 ]
        then
            for n in $(seq 1 $eth)
            do
                sudo ovs-vsctl set interface s${s}-eth${n} ingress_policing_rate=${rate}
                sudo ovs-vsctl set interface s${s}-eth${n} ingress_policing_burst=${burst}
                sudo ovs-vsctl list interface s${s}-eth${n}
            done
        else
            sudo ovs-vsctl set interface s${s}-eth${eth} ingress_policing_rate=${rate}
            sudo ovs-vsctl set interface s${s}-eth${eth} ingress_policing_burst=${burst}
                sudo ovs-vsctl list interface s${s}-eth${eth}
        fi
        ;;
    ?)
        exit
        ;;
esac
