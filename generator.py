import threading
from time import sleep, time
import subprocess

TIMESTAP = 1

def say(something):
    sleep(TIMESTAP)
    print(something)

stats = [0]*3

class SendPacket(threading.Thread):
    def __init__(self, id, cmd, start_time):
        self.id = id
        self.cmd = cmd
        self.start_time = start_time
        threading.Thread.__init__(self)
    
    def run(self):
        sleep(self.start_time)
        start = time()
        subprocess.Popen(self.cmd, stdout=subprocess.PIPE, shell=True).wait()
        end = time()
        stats[self.id-1] = end-start
        print("Thread %s is over and run time: %s"%(self.id, end-start))


if __name__ == "__main__":
    bwu = TIMESTAP*100//8
    cmd = [
        "iperf3 -c 10.0.0.1 -B 10.0.0.2 --cport 12345 -n %sM -p 5201"%(bwu*5),
        "iperf3 -c 10.0.0.1 -B 10.0.0.2 --cport 12346 -n %sM -p 5202"%(bwu*3),
        "iperf3 -c 10.0.0.1 -B 10.0.0.2 --cport 12347 -n %sM -p 5203"%(bwu*1)
    ]
    start_time = [
        0*TIMESTAP, 1*TIMESTAP, 2*TIMESTAP
    ]
    print("Starting...")
    i = 0
    while True:
        print(i)
        i = i+1
        start = time()
        t1 = SendPacket(1, cmd[0], start_time[0])
        t2 = SendPacket(2, cmd[1], start_time[1])
        t3 = SendPacket(3, cmd[2], start_time[2])
        t1.start()
        t2.start()
        t3.start()
        t1.join()
        t2.join()
        t3.join()
        end = time()
        print("Total time: %s"%(end-start))
        print("Average time: %s"%(sum(stats)/3))
        # sleep(10)
        # t3.start()