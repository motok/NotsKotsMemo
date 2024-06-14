#!/bin/sh
#
# /etc/rtsold-A.sh
#

# $1: interface name on which RA received.
# $2: RA-sending router address.

DRLINE=$(netstat -nrf inet6 | grep default)
if [ -z "${DRLINE}" ]
then
        route add -6 default ${2}%${1}
else
        route change -6 default ${2}%${1}
fi
