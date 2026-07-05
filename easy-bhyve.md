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

- 自分の環境だとpsで人様のプロセスが見えないようにしているので、ps/pgrepなどにsudoをつける必要がある。
``` shell
$ diff -u easy-bhyve.orig easy-bhyve
--- easy-bhyve.orig	2026-07-05 14:20:51.559077000 +0900
+++ easy-bhyve	2026-07-05 14:21:08.732027000 +0900
@@ -250,7 +250,7 @@
 }
 
 __check_running () {
-	pgrep -qxf "bhyve: ${system}"
+	${do_sudo} pgrep -qxf "bhyve: ${system}"
 	return $?
 }
 
@@ -357,7 +357,7 @@
 __clear_vm () {
 	local _id _optif _bridge
 
-	if [ ${do_sudo} != echo ] && pgrep -qxf "bhyve: ${system}"
+	if [ ${do_sudo} != echo ] && ${do_sudo} pgrep -qxf "bhyve: ${system}"
 	then
 		echo "*** ${system}: running" >&2
 		exit 2
@@ -380,7 +380,7 @@
 __shutdown_vm () {
 	local _pid _i
 
-	if ! _pid=$(pgrep -xf "bhyve: ${system}")
+	if ! _pid=$(${do_sudo} pgrep -xf "bhyve: ${system}")
 	then
 		echo "*** ${system} is not running" >&2
 		exit 2
@@ -396,7 +396,7 @@
 
 	if [ ${do_sudo} != echo ]; then
 		_i=0
-		while pgrep -qxf "bhyve: ${system}"
+		while ${do_sudo} pgrep -qxf "bhyve: ${system}"
 		do
 			_i=$((_i + 1))
 			if [ ${_i} -ge 120 ]	# shutdownを1分までは待つ
@@ -448,7 +448,7 @@
 		return
 	fi
 
-	if pgrep -qxf "bhyve: ${system}"
+	if ${do_sudo} pgrep -qxf "bhyve: ${system}"
 	then
 		echo "*** ${system}: running" >&2
 		return 2
@@ -500,7 +500,7 @@
 	0)	echo "Usage: ${ebprog} [snapshot] New_VM [New_VM]" >&2
 		return 2 ;;
 
-	1)	if pgrep -qxf "bhyve: ${system}"; then
+	1)	if ${do_sudo} pgrep -qxf "bhyve: ${system}"; then
 			echo "*** ${system}: running" >&2
 			return 2
 		fi
@@ -523,7 +523,7 @@
 			fi
 			;;
 
-		*)	if pgrep -qxf "bhyve: ${system}"; then
+		*)	if ${do_sudo} pgrep -qxf "bhyve: ${system}"; then
 				echo "*** ${system}: running" >&2
 				return 2
 			fi
@@ -647,7 +647,7 @@
 
 __show_bhyve_detail () {
 	echo
-	pgrep -fl bhyve: |
+	${do_sudo} pgrep -fl bhyve: |
 	while read pid dummy vm
 	do
 		printf '%-5d  %-12s  %d  %s\n' ${pid} ${vm} $(__get_mem_and_cpu ${vm})
@@ -655,7 +655,7 @@
 }
 
 __util_stat () {
-	pgrep -d, bhyve >/dev/null 2>&1 && { ps -u -p $(pgrep -d, bhyve); echo; }
+	${do_sudo} pgrep -d, bhyve >/dev/null 2>&1 && { ${do_sudo} ps -u -p $(${do_sudo} pgrep -d, bhyve); echo; }
 
 	[ -d /dev/vmm ] && ls -l /dev/vmm/*

```
