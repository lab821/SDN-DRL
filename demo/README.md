These shells(or windows) are needed to set up an environment.
1. Controller
(py35)~/project/auto/examples$ ryu-manager app/ofctl_rest.py demo_controller.py

2. Mininet
(py35)~/project/auto/examples$ sudo ./mn_topo.sh r sflow

3. sflow
(py35)/opt/sflow-rt$ ./start.sh

4. OVS flow lookup
(py35)~/project/auto/examples$ sudo ovs-ofctl -O OpenFlow13 dump-flows s1

In browser, open these websites to get information about OVS.
1. to get all flows stats: http://localhost:8080/stats/flow/1
2. to get meter stats: http://localhost:8080/stats/meter/1
3. to get meter config or description stats: http://localhost:8080/stats/meterconfig/1
4. to get meter features stats: http://localhost:8080/stats/meterfeatures/1
