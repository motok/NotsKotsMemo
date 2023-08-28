# ミニPCにFreeBSD13.2を入れてSophos Firewall HomeとpfSenseをbhyve上に置く
  

## bhyve上にSophos Firewall Home Editionを入れよう
- ということで、今回のお題は、bhyve上にSophos Firewall Home Edition
  (SFHE)をインストールすること。
- 後述するがSFHEはちょっと古めのNICしか認識しないので、bhyveで仮想化し
  て誤魔化す必要があった。

## ミニPC

- ちょっと前に買った
  [N5105機](https://ja.aliexpress.com/item/1005004302428997.html?spm=a2g0o.order_list.order_list_main.9.333e585aXikXGN&gatewayAdapt=glo2jpn)
  は、2.5Gbps NIC x 4のせいか、定常運用時の温度が高めなのが唯一の欠点
  であった。
- そこで今回はGbEでもいいので熱を持たないものということで、
  [Chatreey T8+](https://ja.aliexpress.com/item/4001166656473.html?spm=a2g0o.order_list.order_list_main.4.333e585aXikXGN&gatewayAdapt=glo2jpn)
  を選択した。
  - Intel N100 (4 core 4 thread・最大3.4GHz・キャッシュ6MB・TDP 6W)
  - メモリ LPDDR5 直付け16GB
  - 128GB SSD
  - GbE x 2 (RealTek)
- 難なくFreeBSDをインストールすることができた。
  - とはいえ、`bsdinstall`でファイルシステムにUFSを選択すると、
    base.txzを展開するあたりでクラッシュして勝手にrebootがかかるようだ。
  - 今回はzfsでインストールしたので、特に問題はなかった。
- しばらく走らせても触るとほんのり温かい程度で、これなら連続稼働しても大丈夫でしょう。
- Chatreey T8+の`/var/run/dmesg.boot`は次の通り。
  ```
  Copyright (c) 1992-2021 The FreeBSD Project.
  Copyright (c) 1979, 1980, 1983, 1986, 1988, 1989, 1991, 1992, 1993, 1994
	  The Regents of the University of California. All rights reserved.
  FreeBSD is a registered trademark of The FreeBSD Foundation.
  FreeBSD 13.2-RELEASE-p2 GENERIC amd64
  FreeBSD clang version 14.0.5 (https://github.com/llvm/llvm-project.git llvmorg-14.0.5-0-gc12386ae247c)
  VT(vga): resolution 640x480
  CPU: Intel(R) N100 (806.40-MHz K8-class CPU)
	Origin="GenuineIntel"  Id=0xb06e0  Family=0x6  Model=0xbe  Stepping=0
	Features=0xbfebfbff<FPU,VME,DE,PSE,TSC,MSR,PAE,MCE,CX8,APIC,SEP,MTRR,PGE,MCA,CMOV,PAT,PSE36,CLFLUSH,DTS,ACPI,MMX,FXSR,SSE,SSE2,SS,HTT,TM,PBE>
	Features2=0x7ffafbbf<SSE3,PCLMULQDQ,DTES64,MON,DS_CPL,VMX,EST,TM2,SSSE3,SDBG,FMA,CX16,xTPR,PDCM,PCID,SSE4.1,SSE4.2,x2APIC,MOVBE,POPCNT,TSCDLT,AESNI,XSAVE,OSXSAVE,AVX,F16C,RDRAND>
	AMD Features=0x2c100800<SYSCALL,NX,Page1GB,RDTSCP,LM>
	AMD Features2=0x121<LAHF,ABM,Prefetch>
	Structured Extended Features=0x239ca7eb<FSGSBASE,TSCADJ,BMI1,AVX2,FDPEXC,SMEP,BMI2,ERMS,INVPCID,NFPUSG,PQE,RDSEED,ADX,SMAP,CLFLUSHOPT,CLWB,PROCTRACE,SHA>
	Structured Extended Features2=0x98c007bc<UMIP,PKU,OSPKE,WAITPKG,GFNI,VAES,VPCLMULQDQ,RDPID,MOVDIRI,MOVDIR64B>
	Structured Extended Features3=0xfc184410<FSRM,MD_CLEAR,IBT,IBPB,STIBP,L1DFL,ARCH_CAP,CORE_CAP,SSBD>
	XSAVE Features=0xf<XSAVEOPT,XSAVEC,XINUSE,XSAVES>
	IA32_ARCH_CAPS=0x80fd6b<RDCL_NO,IBRS_ALL,SKIP_L1DFL_VME,MDS_NO,TAA_NO>
	VT-x: PAT,HLT,MTF,PAUSE,EPT,UG,VPID,VID,PostIntr
	TSC: P-state invariant, performance statistics
  real memory  = 17179869184 (16384 MB)
  avail memory = 16356814848 (15599 MB)
  Event timer "LAPIC" quality 600
  ACPI APIC Table: <ALASKA A M I >
  WARNING: L3 data cache covers more APIC IDs than a package (7 > 3)
  FreeBSD/SMP: Multiprocessor System Detected: 4 CPUs
  FreeBSD/SMP: 1 package(s) x 4 core(s)
  random: registering fast source Intel Secure Key RNG
  random: fast provider: "Intel Secure Key RNG"
  random: unblocking device.
  ioapic0 <Version 2.0> irqs 0-119
  Launching APs: 3 1 2
  random: entropy device external interface
  kbd0 at kbdmux0
  efirtc0: <EFI Realtime Clock>
  efirtc0: registered as a time-of-day clock, resolution 1.000000s
  smbios0: <System Management BIOS> at iomem 0x75cc9000-0x75cc901e
  smbios0: Version: 3.5, BCD Revision: 3.5
  aesni0: <AES-CBC,AES-CCM,AES-GCM,AES-ICM,AES-XTS,SHA1,SHA256>
  acpi0: <ALASKA A M I >
  Firmware Error (ACPI): Could not resolve symbol [\134_SB.PC00.TXHC.RHUB.SS01], AE_NOT_FOUND (20201113/dswload2-315)
  ACPI Error: AE_NOT_FOUND, During name lookup/catalog (20201113/psobject-372)
  Firmware Error (ACPI): Could not resolve symbol [\134_SB.PC00.TXHC.RHUB.SS02], AE_NOT_FOUND (20201113/dswload2-315)
  ACPI Error: AE_NOT_FOUND, During name lookup/catalog (20201113/psobject-372)
  acpi0: Power Button (fixed)
  hpet0: <High Precision Event Timer> iomem 0xfed00000-0xfed003ff on acpi0
  Timecounter "HPET" frequency 19200000 Hz quality 950
  Event timer "HPET" frequency 19200000 Hz quality 550
  Event timer "HPET1" frequency 19200000 Hz quality 440
  Event timer "HPET2" frequency 19200000 Hz quality 440
  Event timer "HPET3" frequency 19200000 Hz quality 440
  Event timer "HPET4" frequency 19200000 Hz quality 440
  attimer0: <AT timer> port 0x40-0x43,0x50-0x53 irq 0 on acpi0
  Timecounter "i8254" frequency 1193182 Hz quality 0
  Event timer "i8254" frequency 1193182 Hz quality 100
  Timecounter "ACPI-fast" frequency 3579545 Hz quality 900
  acpi_timer0: <24-bit timer at 3.579545MHz> port 0x1808-0x180b on acpi0
  pcib0: <ACPI Host-PCI bridge> port 0xcf8-0xcff on acpi0
  pci0: <ACPI PCI bus> on pcib0
  vgapci0: <VGA-compatible display> port 0x6000-0x603f mem 0x6000000000-0x6000ffffff,0x4000000000-0x400fffffff at device 2.0 on pci0
  vgapci0: Boot video device
  xhci0: <XHCI (generic) USB 3.0 controller> mem 0x6001100000-0x600110ffff at device 20.0 on pci0
  xhci0: 32 bytes context size, 64-bit DMA
  usbus0 on xhci0
  usbus0: 5.0Gbps Super Speed USB v3.0
  pci0: <memory, RAM> at device 20.2 (no driver attached)
  pci0: <simple comms> at device 22.0 (no driver attached)
  ahci0: <AHCI SATA controller> port 0x6090-0x6097,0x6080-0x6083,0x6060-0x607f mem 0x80700000-0x80701fff,0x80703000-0x807030ff,0x80702000-0x807027ff at device 23.0 on pci0
  ahci0: AHCI v1.31 with 1 6Gbps ports, Port Multiplier not supported
  ahcich1: <AHCI channel> at channel 1 on ahci0
  pci0: <serial bus> at device 25.0 (no driver attached)
  pci0: <serial bus> at device 25.1 (no driver attached)
  pcib1: <ACPI PCI-PCI bridge> at device 28.0 on pci0
  pci1: <ACPI PCI bus> on pcib1
  re0: <RealTek 8168/8111 B/C/CP/D/DP/E/F/G PCIe Gigabit Ethernet> port 0x5000-0x50ff mem 0x80604000-0x80604fff,0x80600000-0x80603fff at device 0.0 on pci1
  re0: Using 1 MSI-X message
  re0: turning off MSI enable bit.
  re0: ASPM disabled
  re0: Chip rev. 0x54000000
  re0: MAC rev. 0x00100000
  miibus0: <MII bus> on re0
  rgephy0: <RTL8251/8153 1000BASE-T media interface> PHY 1 on miibus0
  rgephy0:  none, 10baseT, 10baseT-FDX, 10baseT-FDX-flow, 100baseTX, 100baseTX-FDX, 100baseTX-FDX-flow, 1000baseT-FDX, 1000baseT-FDX-master, 1000baseT-FDX-flow, 1000baseT-FDX-flow-master, auto, auto-flow
  re0: Using defaults for TSO: 65518/35/2048
  re0: Ethernet address: 68:1d:ef:34:7a:a7
  re0: netmap queues/slots: TX 1/256, RX 1/256
  pcib2: <ACPI PCI-PCI bridge> at device 29.0 on pci0
  pci2: <ACPI PCI bus> on pcib2
  pci2: <network> at device 0.0 (no driver attached)
  pcib3: <ACPI PCI-PCI bridge> at device 29.3 on pci0
  pci3: <ACPI PCI bus> on pcib3
  re1: <RealTek 8168/8111 B/C/CP/D/DP/E/F/G PCIe Gigabit Ethernet> port 0x3000-0x30ff mem 0x80404000-0x80404fff,0x80400000-0x80403fff at device 0.0 on pci3
  re1: Using 1 MSI-X message
  re1: turning off MSI enable bit.
  re1: ASPM disabled
  re1: Chip rev. 0x54000000
  re1: MAC rev. 0x00100000
  miibus1: <MII bus> on re1
  rgephy1: <RTL8251/8153 1000BASE-T media interface> PHY 1 on miibus1
  rgephy1:  none, 10baseT, 10baseT-FDX, 10baseT-FDX-flow, 100baseTX, 100baseTX-FDX, 100baseTX-FDX-flow, 1000baseT-FDX, 1000baseT-FDX-master, 1000baseT-FDX-flow, 1000baseT-FDX-flow-master, auto, auto-flow
  re1: Using defaults for TSO: 65518/35/2048
  re1: Ethernet address: 68:1d:ef:34:7a:a8
  re1: netmap queues/slots: TX 1/256, RX 1/256
  isab0: <PCI-ISA bridge> at device 31.0 on pci0
  isa0: <ISA bus> on isab0
  hdac0: <Intel Alder Lake-N HDA Controller> mem 0x6001110000-0x6001113fff,0x6001000000-0x60010fffff at device 31.3 on pci0
  pci0: <serial bus> at device 31.5 (no driver attached)
  acpi_button0: <Sleep Button> on acpi0
  cpu0: <ACPI CPU> on acpi0
  acpi_button1: <Power Button> on acpi0
  acpi_tz0: <Thermal Zone> on acpi0
  acpi_syscontainer0: <System Container> on acpi0
  acpi_syscontainer1: <System Container> on acpi0
  atrtc0: <AT realtime clock> at port 0x70 irq 8 on isa0
  atrtc0: Warning: Couldn't map I/O.
  atrtc0: registered as a time-of-day clock, resolution 1.000000s
  Event timer "RTC" frequency 32768 Hz quality 0
  atrtc0: non-PNP ISA device will be removed from GENERIC in FreeBSD 14.
  hwpstate_intel0: <Intel Speed Shift> on cpu0
  hwpstate_intel1: <Intel Speed Shift> on cpu1
  hwpstate_intel2: <Intel Speed Shift> on cpu2
  hwpstate_intel3: <Intel Speed Shift> on cpu3
  Timecounter "TSC" frequency 806401102 Hz quality 1000
  Timecounters tick every 1.000 msec
  ZFS filesystem version: 5
  ZFS storage pool version: features support (5000)
  Trying to mount root from zfs:zroot/ROOT/default []...
  ugen0.1: <Intel XHCI root HUB> at usbus0
  uhub0 on usbus0
  uhub0: <Intel XHCI root HUB, class 9/0, rev 3.00/1.00, addr 1> on usbus0
  ada0 at ahcich1 bus 0 scbus0 target 0 lun 0
  ada0: <LuminouTek 128GB V0922A0> ACS-4 ATA SATA 3.x device
  ada0: Serial Number 2303JPDD12800001106
  ada0: 600.000MB/s transfers (SATA 3.x, UDMA6, PIO 512bytes)
  ada0: Command Queueing enabled
  ada0: 122104MB (250069680 512 byte sectors)
  uhub0: 16 ports with 16 removable, self powered
  Root mount waiting for: usbus0
  ugen0.2: <Realtek Bluetooth Radio> at usbus0
  ugen0.3: <CSCTEK USB Audio and HID> at usbus0
  acpi_wmi0: <ACPI-WMI mapping> on acpi0
  acpi_wmi0: cannot find EC device
  acpi_wmi0: Embedded MOF found
  ACPI: \134_SB.WFDE.WQCC: 1 arguments were passed to a non-method ACPI object (Buffer) (20201113/nsarguments-361)
  acpi_wmi1: <ACPI-WMI mapping> on acpi0
  acpi_wmi1: cannot find EC device
  acpi_wmi1: Embedded MOF found
  ACPI: \134_SB.WFTE.WQCC: 1 arguments were passed to a non-method ACPI object (Buffer) (20201113/nsarguments-361)
  ig4iic0: <Intel Alder Lake-M I2C Controller-4> at device 25.0 on pci0
  ig4iic0: Using MSI
  iicbus0: <Philips I2C bus (ACPI-hinted)> on ig4iic0
  ig4iic1: <Intel Alder Lake-M I2C Controller-5> at device 25.1 on pci0
  ig4iic1: Using MSI
  iicbus1: <Philips I2C bus (ACPI-hinted)> on ig4iic1
  iicbus1: <unknown card> at addr 0x10
  iicbus1: <unknown card> at addr 0x67
  ichsmb0: <Intel Alder Lake SMBus controller> port 0xefa0-0xefbf mem 0x6001118000-0x60011180ff at device 31.4 on pci0
  smbus0: <System Management Bus> on ichsmb0
  rtw880: <rtw_8821ce> port 0x4000-0x40ff mem 0x80500000-0x8050ffff at device 0.0 on pci2
  rtw880: successfully loaded firmware image 'rtw88/rtw8821c_fw.bin'
  rtw880: Firmware version 24.8.0, H2C version 12
  bridge0: Ethernet address: 58:9c:fc:10:82:34
  bridge1: Ethernet address: 58:9c:fc:10:bb:33
  lo0: link state changed to UP
  re0: link state changed to DOWN
  re0: link state changed to UP
  re1: link state changed to DOWN
  re1: link state changed to UP
  ubt0 on uhub0
  ubt0: <Bluetooth Radio> on usbus0
  uaudio0 on uhub0
  uaudio0: <CSCTEK USB Audio and HID, class 0/0, rev 2.00/80.07, addr 2> on usbus0
  uaudio0: Play[0]: 48000 Hz, 2 ch, 16-bit S-LE PCM format, 2x8ms buffer.
  uaudio0: Play[0]: 16000 Hz, 2 ch, 16-bit S-LE PCM format, 2x8ms buffer.
  uaudio0: Play[0]: 8000 Hz, 2 ch, 16-bit S-LE PCM format, 2x8ms buffer.
  uaudio0: Record[0]: 48000 Hz, 1 ch, 16-bit S-LE PCM format, 2x8ms buffer.
  uaudio0: Record[0]: 16000 Hz, 1 ch, 16-bit S-LE PCM format, 2x8ms buffer.
  uaudio0: Record[0]: 8000 Hz, 1 ch, 16-bit S-LE PCM format, 2x8ms buffer.
  uaudio0: No MIDI sequencer.
  pcm0: <USB audio> on uaudio0
  uaudio0: No HID volume keys found.
  uhid0 on uhub0
  uhid0: <CSCTEK USB Audio and HID, class 0/0, rev 2.00/80.07, addr 2> on usbus0
  device_attach: uhid0 attach returned 12
  WARNING: attempt to domain_add(bluetooth) after domainfinalize()
  WARNING: attempt to domain_add(netgraph) after domainfinalize()
  re0: promiscuous mode enabled
  bridge0: link state changed to UP
  re1: promiscuous mode enabled
  bridge1: link state changed to UP
  ```

## Sophos Firewall Home Edition
- [Sophos](https://www.sophos.com/ja-jp) はインターネット関連の製品・
  サービスを出している会社で、老舗と言っていいんじゃないか。
- 今だと EDR (XDR,MDR) とファイアウォール(SGとかXGとか)が有名だと思う。
- [Sophos Firewall Home
  Edition](https://www.sophos.com/ja-jp/free-tools/sophos-xg-firewall-home-edition)
  は、商品として出しているファイアウォールをホームユーザなら無料で使っ
  て良いよ、というもの。
  - ただし、サポートは*ない*。(まあ当然ではあるけど、そんなに剣もほろ
    ろにしなくてもいいじゃないですか、と誰にともなく。)
- SFHE の「システム要件」は上記のURLにある通りで、
  - Intel 互換コンピュータで NIC が２枚必要。
  - 4 core までの CPU と 6 GB までの RAM。これを越えるコアやメモリがあっ
    ても単に使わない。
  - 明記されていないが、メモリは最低でも 4 GB ないとインストーラが文句
    を言ってインストールできない。
  - ストレージについて言及はないが、手元で `SW-19.5.1_MR-1-278` をイン
    ストールしたところ、1.32 GB を使っている。ログや一時ファイルの領域
    やバージョンアップ用の領域を考えても 5 GB か 10 GB あれば足りるん
    じゃないかしら。
	- [このページ](https://doc.sophos.com/nsg/sophos-firewall/18.5/help/en-us/webhelp/onlinehelp/VirtualAndSoftwareAppliancesHelp/SoftwareAppliance/index.html)
      だと、HDD or SSDは最低10GBで64GBを推奨になっている。
- インストール時に、破壊的にストレージ全体を使うので、元々の内容は必要
  ならバックアップしておくこと。
- あと、これも言及はないが、新し目の NIC には対応していないみたい。
  - 手元では Intel I226V は認識しなかった。
  - 仕方がないので、FreeBSD 13.2R を入れて、SFHE を bhyve ゲストとして
    インストールしようという趣向に相成りました。
  - これを書いている時点の SFHE のバージョンは `SW-19.5.1_MR-1-278` 。
    そうこうしているうちに`SW-19.5.2-624`が出た。

## bhyve管理ツールの_bhyve
- bhyveを扱うために管理ソフトの
  [_bhyve](https://github.com/belgianbeer/_bhyve)
  をインストールした。`_`の有無に注意。
- といっても、githubからもらってきて`~/local/_bhyve/`以下に展開するだけ。
- その後の設定ファイル作成やISO置き場作成なども含めて次のようなディレ
  クトリ構成にして、`~/local/_bhyve`と`~/local/_bhyve/bhyve`をPATHに加
  えておく。
  ```
  $ ls ~/local/_bhyve/
  _bhyve*              _bhyve.conf          README.md
  _bhyve-example.conf  bhyve/
  _bhyve-list*         ISO/
  ```
- `_bhyve`の設定(`_bhyve.conf`)はこんな感じ。
  ```
  # setting example for _bhyve

  # ISO Images
  iso_path=~moto/local/_bhyve/ISO		# ISO image のあるPathのprefix

  iso_freebsd132=FreeBSD-13.2-RELEASE-amd64-disc1.iso
  iso_sophos_fw_home=SW-19.5.1_MR-1-278.iso
  iso_pfsense=pfSense-CE-2.7.0-RELEASE-amd64.iso

  # ------------------------------------------------------------
  #  Default リソース
  #
  bridge=bridge0		# default bridge
  netif=re0		# default bridgeの物理IF
 			  # ${bridge}の物理IFに割り当てられる
  volroot=zroot/vm	# VM用ZFS Volumeのprefix
			  # UFSの場合 volroot=/vm とする

  # Sophos FW Home
  sophos0_id=0    # VMのidは0番
  sophos0_cpu=4   # cpu coreは4個
  sophos0_mem=6G  # メモリ6GB
  sophos0_cd0=${iso_path}/${iso_sophos_fw_home}    # インストール用のCDイメージ
  #sophos0_if0=tap0	# Sophosから見て最初のNICでLAN側の役割。このtap0と次のbridge0は_bhyveの既定値なので書かなくても可。
  #sophos0_if0_bridge=bridge0 # _bhyveの機能でtap0はbridge0にaddmされる。ホスト側設定(rc.conf)で物理NICをbridge0にaddmすれば繋がる。
  sophos0_if1=tap1	# Sophosから見て２番目のNICでWAN側の役割。
  sophos0_if1_bridge=bridge1
  #sophos0_grub_boot="insmod linux; linux /19_5_1_278"
  sophos0_grub_boot="insmod linux; linux /19_5_2_624" # ブート時にgrub loaderに渡すコマンド。
  # grub_boot: configfile=(hd0,4)/boot/grub/grub.cfg  # ゲスト側のgrub.confを参照できるといいなと試行錯誤中。

  # 素のFreeBSD。試験用
  freebsd0_id=1
  freebsd0_freebsd=YES
  freebsd0_if0=tap10
  freebsd0_if0_bridge=bridge0
  freebsd0_cd0=${iso_path}/${iso_freebsd132}

  # ついでにpfSense。要はFreeBSDなので_bhyveの設定としては特に変わったことはない。
  # 既定値のLAN/WANの配置がSophosと逆らしいのと、LAN側のDHCPサーバの帯域が192.168.1.0/24で上流のPR-500KIと衝突する点には注意。
  pfsense0_id=2
  pfsense0_freebsd=YES
  pfsense0_cpu=4
  pfsense0_mem=6G
  pfsense0_if0=tap20	# LAN
  pfsense0_if0_bridge=bridge0
  pfsense0_if1=tap21	# WAN
  pfsense0_if1_bridge=bridge1
  pfsense0_cd0=${iso_path}/${iso_pfsense}
  ```
- ISOの下にはインストールメディア(cdイメージ)を置いておく。
- これで一度`_bhyve`コマンドを実行すると`~/local/_bhyve/bhyve/`の下に
  `sophos0-boot`のようなコマンドがぞろぞろ並ぶ。
  - 初回だけ `sophos0-resources -V 20G -s`のようにしてディスク領域確保
  - `sophos0-install`でVMのOSをインストール
  - `sophos0-boot`でできたVMを起動、`sophos0-ttyboot`ならコンソールア
    クセスを保ったまま起動。
  - `sophos0-shutdown`でVMをshutdown。
  - 稼働中のVMのコンソールを使うなら`sophos0-console`
  - `sophos0-consol`からホストのコマンドラインへ戻るには、
    要は`cu`で接続しているので`~.`で戻る。
	`ssh`でログインした先で`sophos0-console`している場合は`~~.`のように
	ティルダをエスケープする必要がある。
  - 詳しくは`_bhyve`のgithubやそこからリンクされたスライドを見てくださ
    い。
- `_bhyve-list`は、rcscriptのstatus部分を切り出したようなコマンドで、
  `_bhyve`上で稼働中のVMを列挙するもの。`service _bhyve status`すれば
  同じこと。
  - なんだけど、`/etc/sysctl.conf`で`security.bsd.see_other_[ug]ids=0`を設定していると、
    つまり、一般ユーザの場合に自分のプロセスしか見えない状態にしていると`pgrep`に`sudo`が必要とか
	ちょっと細かい調整が必要。現在調査中。
	```
	#!/bin/sh

    _bhyve_dir="/home/moto/local/_bhyve"

    __get_mem_and_cpu () {
        (
            eval $(${_bhyve_dir}/bhyve/$1-resources)
            echo $cpu $mem
        )
    }

    sudo pgrep -fl bhyve: \
    | while read pid dummy vm
      do
        printf '%-5d %-10s %d %s\n' ${pid} ${vm} $(__get_mem_and_cpu ${vm})
      done \
    | sort +1
    ```

## _bhyveを動作させるためのホスト側設定
- `_bhyve`とNIC関連の`/etc/rc.conf.local`は以下のような感じ。
- `_bhyve`をboot時に自動で起動するrcscriptはこれ。
  - re0がLAN側でre1がWAN側。
  - re1は上流からDHCPなどで設定をもらう。
  - bridge[01]を作っておいて、re[01]をaddmさせる。
  - VMが立ち上がる時にホスト側でいうtap0などを作成してbridge[01]にaddm
    させることになるので、re0にはホスト側ではIPアドレスを設定せず、VM
    側でIPアドレスを設定する。
  ```
  (/etc/rc.conf.localで)
  _bhyve_enable="YES"                      # デーモン自動起動
  _bhyve_dir="/home/foobar/local/_bhyve"   # コマンド・設定の場所
  _bhyve_vm_list="sophos0"                 # 自動起動するVM名

  cloned_interfaces="bridge0 bridge1"      # bridge[01]を作成
  autobridge_interfaces="bridge0 bridge1"  # 自動でifを追加せよ
  autobridge_bridge0="re0"                 # 具体的にはこれよ
  autobridge_bridge1="re1"

  ifconfig_bridge0="inet 172.16.16.253/24 description LAN_BRIDGE"
  ifconfig_bridge0_ipv6="inet6 accept_rtadv" # ここは自分がIPv6のDHCPサーバになるべき？
  ifconfig_bridge1="inet 192.168.1.253/24 description WAN_BRIDGE"
  ifconfig_bridge1_ipv6="inet6 accept_rtadv"

  ifconfig_re0="description LAN_PHY_IF"      # re0はLAN側。FreeBSDのブリッジ設定ではメンバーNICではなくブリッジにIPアドレスを持つようにするのでここはdescだけ。
  ifconfig_re0_ipv6="inet6 accept_rtadv"     # 
  ifconfig_re1="description WAN_PHY_IF"      # re1はWAN側。
  ifconfig_re1_ipv6="inet6 accept_rtadv"     # IPv6も上流からもらう、けど、多分これもブリッジでやるべき。
  ```
- `_bhyve`のrcscript (`/usr/local/etc/rc.d/_bhyve`)はこれ。
  - 確かどこかでいただいてきてちょっといじったやつなんだけど、ちょっと
    思い出せない。ありがたく使わせていただいています。
  - あ、時々sudo要否が怪しいのは僕の環境(一般ユーザには自分のプロセス
    しか見えない)のせいです。
  - 先頭付近で環境変数TERMを設定しているのは、これがないとboot時に刺さ
    るせい。vt100は適当。
  ```
  #!/bin/sh
  #
  # $FreeBSD$

  # PROVIDE: _bhyve
  # REQUIRE: NETWORKING SERVERS dmesg
  # BEFORE: dnsmasq
  # KEYWORD: shutdown nojail

  . /etc/rc.subr

  # It seems no TERM during boot, and grub requires it.
  TERM=vt100
  export TERM

  : ${_bhyve_enable="NO"}
  : ${_bhyve_dir="/home/moto/local/_bhyve"}
  : ${_bhyve_vm_list=""} # space separated list of _bhyve vms.

  name=_bhyve
  desc="Start and stop _bhyve guests on boot/shutdown"
  rcvar=_bhyve_enable

  load_rc_config $name

  command="${_bhyve_dir}/${name}"
  start_cmd="${name}_start"
  stop_cmd="${name}_stop"
  status_cmd="${name}_status"

  _bhyve_start()
  {
	  for vm in ${_bhyve_vm_list}
	  do
		  ${_bhyve_dir}/bhyve/${vm}-boot
	  done
  }

  _bhyve_stop()
  {
	  for vm in ${_bhyve_vm_list}
	  do
		  ${_bhyve_dir}/bhyve/${vm}-shutdown
	  done
  }

  __get_mem_and_cpu () {
	  (
		  eval $(${_bhyve_dir}/bhyve/$1-resources)
		  echo $cpu $mem
	  )
  }

  _bhyve_status()
  {
	  pgrep -fl bhyve: \
	  | while read pid dummy vm
	  do
		  printf '%-5d %-10s %d %s\n' ${pid} ${vm} $(__get_mem_and_cpu ${vm})
	  done \
	  | sort +1
  }

  run_rc_command "$1"
  ```

## あとがき
- これでChatreey T8+上のFreeBSD-13.2RのbhyveゲストとしてSophos Firewall Home Editionが動作するはず。
- Sophosをちょっと触ってみた感触としては、よくわからん。
  - ゾーンって何？どこで定義してるの？
  - `deny all from any to any`みたいなルールはどこで書くんや？
  - このポリシー、有効なの無効なの？
  - Sophos Centralに登録して使えという割に、ログインできたりできなかったりでちょっと認証廻りがおかしくないっすか？
  - パスワードリセットの最後のところで新しいパスワードを２回書いてクリックスルーしたら、認証失敗って言われるのはなんで？
- というわけで、ハードウェア調達や`_bhyve`の設定やTERM変数が必要なことをググり倒して天啓を受けるとか
  苦労して動かした割には脱力感でいっぱいです。
- URLのカテゴリ別制御とかには期待してたんすけどね。
