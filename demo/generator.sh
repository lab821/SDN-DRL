#!/bin/bash

logfile="log/generator_"`date +%Y%m%d%H%M`".log"

python -u generator.py | tee ${logfile}