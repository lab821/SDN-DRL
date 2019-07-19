from __future__ import print_function
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, CPULimitedHost, OVSKernelSwitch
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
import os
import pdb
import subprocess

class DumbbellTopo(Topo):
    "Dumbbell Topology"
    def build(self, n=2):
        switch1 = self.addSwitch('s1', cls=OVSKernelSwitch, protocols='OpenFlow13')
#        switch2 = self.addSwitch('s2')
        host = self.addHost('h1', ip='10.0.0.1')
#linkopts = dict(bw=10, delay='5ms', loss=2,  max_queue_size=1000, use_htb=True)
        linkopts = dict(bw=10)
        self.addLink(host, switch1, **linkopts)
        host = self.addHost('h2', ip='10.0.0.2')
        self.addLink(host, switch1)
#        host = self.addHost('h3')
#        self.addLink(host, switch1)
#        host = self.addHost('h4')
#        self.addLink(host, switch1)

def simpleTest():
    topo = DumbbellTopo(n=4)
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink, 
                    controller=lambda name: RemoteController(name, ip='127.0.0.1'))
    net.start()
    print("Dumping host connections")
    dumpNodeConnections(net.hosts)
    print("Testing network connectivity")
    # os.system("./config_queue.sh")
    net.pingAll()
    h1, h2 = net.get('h1', 'h2')
#    pdb.set_trace()
#    h1.cmd('iperf -c %s -u -n 200M -i 1 -b 20M'%(h2.IP()))
#    h2.cmd('iperf -s -u')
    print("Start iperf...")
    h2.sendCmd("iperf -s -u")
    h1.cmdPrint("iperf -c %s -u -n 20 -i 1 -b 2"%(h2.IP()))
    net.iperf((h1, h2))
    os.system("./destroy_queue.sh")

    net.stop()
    os.system("sudo ovs-vsctl -- --all destroy qos -- --all destroy queue")

if __name__ == '__main__':
    setLogLevel('info')
    simpleTest()

