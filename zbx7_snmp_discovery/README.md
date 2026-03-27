# Zabbix7でSNMPディスカバリ

## あらすじ

ひょんなことから、Zabbix7 を建てて SNMP によるデータ収集をすることになった。
それなりにハマったので、覚書を残しておきたい。

## 環境

- [倍控社の迷你工控机](https://bkhdpc.com/jisuanji/)の古いやつで、
  G30B-N5105だと思われる筐体。
  - いわゆるミニPCで、ファンレス。
  - Celeron N5105 / 16GB メモリ / 128GB SSD / 2.5Gbps LAN * 4
  - 2.5Gbps のルータにしようかと思ったら Intel I226-V で、通信ブツ切れ
    でどうにもならないやつだった。Ubuntuだとちょっとマシみたい。
- [Ubuntu 24.04 LTS Server](https://jp.ubuntu.com/download)
  - 24.04.4 LTS (Noble Numbat)
  - apt upgrade済み
- [PostgreSQL 16.13](https://www.postgresql.org/about/news/postgresql-183-179-1613-1517-and-1422-released-3246/)
  - apt でパッケージをインストール
- [TimescaleDB 2.25.2](https://www.tigerdata.com/docs/self-hosted/latest/install/installation-linux#install-timescale_db-on-linux)
  - TimescaleDBのリポジトリを追加して、そこからパッケージをインストール。
- [Zabbix 7.0 LTS](https://www.zabbix.com/download?zabbix=7.0&os_distribution=ubuntu&os_version=24.04&components=server_frontend_agent_2&db=pgsql&ws=nginx)
  - 7.0 LTS / Ubuntu / 24.04 (Noble) / Server, Frontend, Agent2 / PostgreSQL / Nginx
  - パッケージをダウンロードして dpkg -i でインストール。
- [RTX1300](https://network.yamaha.com/products/routers/rtx1300/index)
  - これをZabbixからSNMPで監視(データ収集)しようとしている。
  - [RTX1300 SNMP MIBリファレンス](https://www.rtpro.yamaha.co.jp/RT/docs/snmp/snmp_mib_rtx1300.html)
  - ご家庭で使う10Gbps対応のルータとしては、これか
    [IX-R2530](https://jpn.nec.com/univerge/ix-nrv/info/r2530.html)
    かか。どっちにしてもパパのお小遣いではちょっとムリかも。
- [NVR510](https://network.yamaha.com/products/routers/nvr510/index)
  - これもZabbixからSNMPで監視する対象として。
  - [NVR510 SNMP MIBリファレンス](https://www.rtpro.yamaha.co.jp/RT/docs/snmp/snmp_mib_nvr510.html)
- [NetSNMP](https://www.net-snmp.org)と各種MIB定義ファイル
  - snmp-mibs-downloaderパッケージも併せてaptでインストール。
  - RTX1300のMIB定義ファイルももらってきて、これは手動でインストール。
    - [YAMAHA private MIB](https://www.rtpro.yamaha.co.jp/RT/docs/mib/)
      の
      [Archive file of all private MIB files.](https://www.rtpro.yamaha.co.jp/RT/docs/mib/yamaha-private-mib.tar.gz)
      を入れたので、YAMAHAのネットワーク機器なら大体大丈夫のはず。
  - snmptranslateやsnmpwalkなどを用いてRTX1300と通信できるように両側で
    設定しておく。

## ホストディスカバリ





## 





