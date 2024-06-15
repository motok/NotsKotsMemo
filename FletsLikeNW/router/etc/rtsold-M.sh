#!/bin/sh -x
#
# /etc/rtsold-M.sh
#

# $1: interface name on which RA received.
# $2: RA-sending router address.

# default route is configured in rtsold-A.sh

service dhcp6c restart
