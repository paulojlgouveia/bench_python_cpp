
FROM alpine:edge


RUN apk add --no-cache bind-tools \
						bash \
						iperf3 \
						tcpdump \
						iptables \
						tshark


WORKDIR /tmp/


ADD ./parse_single.sh /tmp/

RUN chmod +x parse_single.sh


# ENTRYPOINT ["/usr/bin/iperf3", "-s"]
