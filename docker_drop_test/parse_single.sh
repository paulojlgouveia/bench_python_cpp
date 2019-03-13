#!/bin/bash

echo $1 $2
tshark -r $1 -q -z io,stat,$2,\
"COUNT(frame) frame",\
"COUNT(tcp.analysis.retransmission)tcp.analysis.retransmission",\
"COUNT(tcp.analysis.duplicate_ack)tcp.analysis.duplicate_ack",\
"COUNT(tcp.analysis.lost_segment)tcp.analysis.lost_segment",\
"COUNT(tcp.analysis.fast_retransmission)tcp.analysis.fast_retransmission"
