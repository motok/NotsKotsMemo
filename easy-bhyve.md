# easy-bhyve メモ

- easy-bhyveは、
  - belgianbeerさんが公開しておられるBhyve管理ツール
  - [https://github.com/belgianbeer/easy-bhyve](https://github.com/belgianbeer/easy-bhyve)

- ちょっとだけ手を入れて使っているので、その要点をメモ。

- rc script
``` shell
$ cat /usr/local/etc/rc.d/easy_bhyve 
#!/bin/sh

# PROVIDE: easy_bhyve
# REQUIRE: NETWORKING SERVERS
# KEYWORD: bhyve easy_bhyve shutdown

# variables in /etc/rc.conf
# 
# easy_bhyve_enable (bool): Set it to YES to enable easy_bhyve rc script.
#                           Default: NO
# easy_bhyve_vms (list of strings): VM names to handle.
#                           Default: (none)
#                           Example: "vm1 vm2"

. /etc/rc.subr

name=easy_bhyve
start_cmd="${name}_start"
stop_cmd="${name}_stop"
status_cmd="${name}_status"

cmd_dir="/home/moto/easy-bhyve"

easy_bhyve_start()
{
	for vm in ${easy_bhyve_vms}
	do
		${cmd_dir}/eb/${vm}-boot
	done
}

easy_bhyve_stop()
{
	date >> /var/tmp/easy-bhyve.log

	if [ -d /dev/vmm ]
	then
		for i in /dev/vmm/*
		do
			vm=$(basename ${i})
			${cmd_dir}/eb/${vm}-shutdown >> /var/tmp/easy-bhyve.log 2>&1
		done
	fi
}

easy_bhyve_status()
{
	${cmd_dir}/easy-bhyve
}

load_rc_config ${name}
run_rc_command "$1"
```
