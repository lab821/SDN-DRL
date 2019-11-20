# Record Information of the Log

### trace200.txt

使用PageRank生成的流量信息，总共3台主机，1500条流；

流量模式是将15条流重复100次，最长的流51.68MB，最短的流1.61MB；

每次重复的时间间隔为32888；

### trace1000.txt

使用PageRank生成的流量信息，总共3台主机，15000条流；

流量模式是将15条流重复1000次，最长的流51.68MB，最短的流1.61MB；

每次重复的时间间隔为32888；

### record

| NO | finished flows | train log | description |
| :-: | :-: | :-: | :-: |
| 1 | log_20191111_1.txt | train_log_20191111_1.txt | 使用trace200.txt |
| 2 | 20191112_log_1.txt | 20191112_train_log_1.txt | 使用trace1000.txt，因为字典大小改变出现运行时错误，而中途中断 |