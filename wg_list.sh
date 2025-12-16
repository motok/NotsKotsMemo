#! /bin/sh

# wg_list.sh
#
# parsing `wg show` output into tab-separated table.
# use like `sudo wg show | ./wg_list.sh`.
# remember that ever-down tunnel will now show.

awk '

function timestr2second (str) {

	if (match(str, /^ *[0-9]+ seconds? ago$/) > 0) {
		split(str, a)
		seconds =  a[1]
	} else if (match(str, /^ *[0-9]+ minutes?, [0-9]+ seconds? ago$/) > 0) {
		split(str, a)
		seconds =  a[1] * 60 + a[3]
	} else if (match(str, /^ *[0-9]+ hours?, [0-9]+ minutes?, [0-9]+ seconds? ago$/) > 0) {
		split(str, a)
		seconds =  a[1] * 3600 + a[3] * 60 + a[5]
	} else if (match(str, /^ *[0-9]+ days?, [0-9]+ hours?, [0-9]+ minutes?, [0-9]+ seconds? ago$/) > 0) {
		split(str, a)
		seconds =  a[1] * 86400 + a[3] * 3600 + a[5] * 60 + a[7]
	} else {
		seconds = -1
	}
	return seconds
}

BEGIN {
	OFS = "\t"
	print "#interface	listen_port	endpoint	allowed_ips	latest_handshake(sec)	lt_5min"
}

/^interface:/ { WG_IF = $2 }

/^ *listening port:/ { WG_PORT = $3 }

/^ *endpoint:/ { END_POINT = $2 }

/^ *allowed ips:/ {
	ALLOWED_IPS = ""
	for (i=3; i<=NF; i++) {
		ALLOWED_IPS = ALLOWED_IPS " " $i
	}
}

/^ *latest handshake:/ {
	LATEST_HS = ""
	for (i=3; i<=NF; i++) {
		LATEST_HS = LATEST_HS " " $i
	}
	
	seconds = timestr2second(LATEST_HS)
	print WG_IF, WG_PORT, END_POINT, ALLOWED_IPS, seconds, ((seconds<300 && seconds>=0) ? "True" : "False")
}

' $*
