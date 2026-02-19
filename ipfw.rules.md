# サーバが自機を守るipfwルールの例

- 2026-02-21 ごろ書いた

## あらすじ

FreeBSD 14.3R で httpd や DNS リゾルバを動かすサーバを建てたとして、
このサーバ用の基本的なアクセスリストを ipfw で書く場合のひとつの例を
考える。
一つの例なので、これで問題ないかどうかは各自の環境と照らし合わせてください。

## サーバの構成

```
           Internet
               |
              HGW
               | 192.0.2.1
               | 2001:db8::1/64
               |
      ==+======+=================+===  192.0.2/24, 2001:db8::/64
        |                        |
        |re0:192.0.2.100         |
	|    2001:db8::100/64    |
       サーバ                   他のノード
```

  - ホームゲートウェイ(HGW)を介してインターネットと繋がっているような状況を想定。
    - HGWの内側のIPアドレスは192.0.2.1/24
  - 内側セグメント 192.0.2/24 にサーバがあって次のサービスを提供しているものとする。
    - DNS リゾルバ (53/tcp, 53/udp)
    - NTP (123/udp)
    - Web サーバ (80/tcp, 443/tcp)
    - SSH サーバ (22/tcp)
    - (サービスではないが、自身へのping (ICMP echo request)には応答する)
  - このサーバに次のようなアクセスリストを ipfw で与える。
    - サーバ内部から外部へのアクセスは全て許可
    - サーバ外部から内部へのアクセスは原則として禁止
    - 上記のサービスについては、内部ネットワーク 192.0.2/24 向けに提供する。

## ipfw ルールの例

```
 #
# /etc/ipfw.rules
#

# 既存のルールとテーブルをすべて削除する。
ipfw -f flush
ipfw table all destroy

# 素通しにするインタフェースをテーブルに登録する。
# 今回はre0でアクセスを制限するので、それ以外のインタフェースを列挙する。
ipfw table OPEN_IF create or-flush type iface
ipfw table OPEN_IF add lo0
ipfw table OPEN_IF add ipfw0

# このIPアドレスからの通信は問答無用で叩き落とす！というIPアドレスをテーブルに登録する。
# そんなIPアドレスは未だないので、テーブルは空の状態。
ipfw table BAD_IP create or-flush

# このポート番号が送信元または送信先にある通信は問答無用で叩き落とす！というIPアドレスをテーブルに登録する。
# 今回はルータではないので単なる例示に過ぎないが、Windows系のポートを止める例。
# 肌理細かくやるならTCPとUDPに分けて考えるべきだが、まぁ例示なのでご勘弁を。
ipfw table BAD_PORT create or-flush type number
ipfw table BAD_PORT add 135
ipfw table BAD_PORT add 137
ipfw table BAD_PORT add 138
ipfw table BAD_PORT add 139
ipfw table BAD_PORT add 445
ipfw table BAD_PORT add 3389

# 自身が提供するサービスを使っても良いIPアドレスブロックをテーブルに登録する。
# ここでは、内部ネットワークの192.0.2/24と2001:db8::/64へのサービス提供。
ipfw table BENEFICIARY_IP create or-flush
ipfw table BENEFICIARY_IP add 192.0.2.0/24
ipfw table BENEFICIARY_IP add 2001:db8::/64

# 自身が提供するサービスのポート番号をテーブルに登録する。
# まずはTCPのもの。
ipfw table SERVICE_TCP create or-flush type number
ipfw table SERVICE_TCP add 53
ipfw table SERVICE_TCP add 80
ipfw table SERVICE_TCP add 443
ipfw table SERVICE_TCP add 22

# 次にUDPのもの。
ipfw table SERVICE_UDP create or-flush type number
ipfw table SERVICE_UDP add 53
ipfw table SERVICE_UDP add 123

# ここからルールの記述を始める。

# まずは、素通しにするインタフェースを通過するすべての通信を許可する。
ipfw add 100 // ----- open interfaces -----
ipfw add 100 allow all from any to any via "table(OPEN_IF)"

# このテーブルに載っているIPアドレスとの通信は、問答無用で叩き落とす。
ipfw add 200 // ----- block BAD_IP -----
ipfw add 200 deny log all from "table(BAD_IP)" to any
ipfw add 200 deny log all from any to "table(BAD_IP)"

# これらのテーブルに載っているポートとの通信は問答無用で叩き落とす。
ipfw add 300 // ----- block BAD_PORT -----
ipfw add 300 deny log tcp from any to any lookup dst-port BAD_PORT
ipfw add 300 deny log tcp from any to any lookup src-port BAD_PORT
ipfw add 300 deny log udp from any to any lookup dst-port BAD_PORT
ipfw add 300 deny log udp from any to any lookup src-port BAD_PORT

# スプーフィング防止のルール。
ipfw add 400 // ----- anti-spoof -----
ipfw add 400 deny log all from any to any not antispoof

# IPv6で必須の通信を許可する。
ipfw add 500 // ----- IPv6 mandatories -----
ipfw add 500 allow ipv6-icmp from :: to ff02::/16
ipfw add 500 allow ipv6-icmp from fe80::/10 to fe80::/10
ipfw add 500 allow ipv6-icmp from fe80::/10 to ff02::/16
ipfw add 500 allow ipv6-icmp from any to any icmp6types 1,2,135,136

# 下の方で keep-state した通信の後続パケットをこの check-state で許可する。
ipfw add 990 // ----- check-state -----
ipfw add 990 check-state

# 自身が提供するサービスのポートに入ってくるパケットを許可して keep-state する。
# その送信元IPアドレスは、サービス提供先のみ。
# 他方で、どこからのものでも ping には応答する。
ipfw add 1000 // ----- service ports -----
ipfw add 1000 allow tcp from "table(BENEFICIARY_IP)" to me lookup dst-port SERVICE_TCP setup keep-state
ipfw add 1000 allow udp from "table(BENEFICIARY_IP)" to me lookup dst-port SERVICE_UDP keep-state
ipfw add 1000 allow icmp from any to me icmptypes 8 keep-state
ipfw add 1000 allow ipv6-icmp from any to me icmp6types 128 keep-state

# 自身から外部へ出ていく通信をほぼすべて許可して keep-state する。
# ICMP[46]のタイプを絞っているのはtimestamp request/reply みたいなやつを禁止するため。
# IPv6の546/udpはDHCPv6なので許可してある。
ipfw add 50000 // ----- egress packets from me -----
ipfw add 50000 skipto 65500 tcp from me to any setup keep-state
ipfw add 50000 skipto 65500 udp from me to any       keep-state
ipfw add 50000 skipto 65500 icmp from me to any icmptypes 0,3,4,5,6,8,11,12,30 keep-state
ipfw add 50000 skipto 65500 ipv6-icmp from me to any icmp6types 1,2,3,4,128,130,131,132,133,134,141,142,143,151,152,153 keep-state
ipfw add 50000 skipto 65500 udp from fe80::/10 to me 546 keep-state

# 明示的に許可しなかったパケットを禁止する。
ipfw add 65000 // ----- default deny -----
ipfw add 65000 deny log all from any to any

# ルール 50000 からスキップしてきたパケットは許可する。
ipfw add 65500 // ----- allow any that jumps in -----
ipfw add 65500 allow ip4 from any to any

```

## あとがき

IPアドレスをドキュメント用のものに変えたりルールの構成を見直したりしたので、
ひょっとしたら正しく動かなくなっているかもしれない。
今度どこかで使う時には確認してようと思う。
しかし、大筋の考え方はここで述べた通りで大丈夫なはず。
だめだったら、こっそり優しくご指摘を請う。
