# UFS on GELI

## これは何？
しばらく使っていなかった自宅サーバを復活させるに当たり、
HDDだけは暗号化しておこうと思ってやってみた。

なんで暗号化したいか？と言えば、
HDDを廃棄する時にデータを消去するのに、例えば
`dd if=/dev/zero of=/dev/daN bs=1024x1024` 
などとしていて、ちゃんとやろうとすると/dev/randomからのデータで
上書きしたり、パターンを変えつつ何度か上書きするようなことをやっていた。
でも、HDDのサイズが大きくなると非常に長い時間を要する。
これは辛い。

そこで、暗号学的消去なる手法を使って時短を図ろうというのが今回のお題。
ディスクを暗号化してから使っていれば、そのまま処分してもデータが漏れることには
ならない、何故ならば、暗号化されているので復号されない限りは大丈夫という理屈。

これがSSDだとSecure Erase機能を使って制御コマンド１発で消せるので、
問題になるような長い時間はかからない。
もっとも、
[Secure Eraseでクリアしているのはマッピングテーブルだけであって、
チップレベルではデータが保持されている
可能性](https://qiita.com/belgianbeer/items/ecd070a649d859143e59)
が指摘されていたりするので、
SSDであってもディスク暗号化を検討するべきかもしれない。

以下でいくつかのパターンを試してみるが、すべてFreeBSD 14.2p2で実行している。
``` shell
# freebsd-version -kru
14.2-RELEASE-p1
14.2-RELEASE-p1
14.2-RELEASE-p2
```

## 試しにやってみるディスク暗号化

まずは`mdconfig`を使ってディスク暗号化なしの試験用ディスクを
作成して少し触ってみることにする。

- `truncate`で扱いやすいサイズのイメージファイルfoo.imgを作成、
  今回は100MBにした。
- これをバックエンドにしたmdデバイスを作成。今回は/dev/md0が生えた。
- `newfs`でmd0にファイルシステムを作成。
- /mntにマウントして、適当な名前と内容でファイルを作成する。
- `umount`して、`mdconfig`でmdデバイスも削除する。

``` shell
# cd /var/tmp
# truncate -s 100m foo.img
# mdconfig -a -t vnode -f foo.img
md0
# newfs /dev/md0
# mount /dev/md0 /mnt
# echo "THIS IS A MARKER." > /mnt/README.txt
# umount /mnt
# mdconfig -d -u 0
```

これで、生ディスク役のfoo.imgにファイルシステムを作成してあって、
その中には適当なファイル(README.txt)がある、という状況ができた。

では、foo.imgを探索すれば、ファイル名(README.txt)やその内容("THIS IS A
MARKER.")を復元することができるのか？できるのである。

``` shell
# strings foo.img | grep README
README.txt
# strings foo.img | grep "THIS IS A MARKER."
THIS IS A MARKER.
```

ということは、このディスク(役のfoo.img)を処分したら、その中のファイル
の内容などは復元できることになり、内容によっては情報漏洩事故になる。

その対策として、ディスクの暗号化をやってみよう。

- イメージファイルbar.imgを作って`mdconfig`でデバイス化するところまで
  は先ほどと同じ。
- GELIを使って暗号化するためのパスフレーズと暗号鍵を作成する。
  - パスフレーズはbar.passに書いておく。
  - bar.keyの暗号鍵は事実上変更できないので、強い乱雑さを持たせておく。
  - 実際にディスク暗号化に使う鍵はここでのbar.keyの方で、
    これを保護するためにパスフレーズ(bar.pass)を使うということらしい。
  - 運用上パスフレーズを変更したい時ても暗号鍵は変わらないのでディスク
    全体を再暗号化するようなことにはならない。
  - パスフレーズも暗号鍵も分割して何人かが集まらないと復号できないよう
    な運用もできるらしいが、今回は割愛。
- `geli init`でmd0を初期化する。パスフレーズと暗号鍵のファイルを指定し
  ている点に注目。これで、md0はディスク暗号化で保護された状態になった。
- 暗号化済みのディスクmd0を使う時には、パスフレーズと暗号鍵を使って
  `geli attach`しないといけない。
  これによって、/dev/md0.eliというデバイスが生えてくる。
  通常の操作は、このmd0.eliデバイスに対して行うことになる。
- `dd`でランダムなバイト列をmd0の全域に書き込む。
  これは、GELI的初期化の前のディスクの内容が残らないように上書きしてお
  くということだと思う。新品のディスクや上書き済みのディスクなどではや
  らなくてもいいかも。
- 生えてきたmd0.eliに対して`newfs`でファイルシステムを作成。
- /dev/md0.eliを/mntにマウント。
- 適当な名前と内容でファイルを作成。
- `umount`してから、`geli detach`で保護状態に戻す。
- `mdconfig`でmdデバイスも削除する。

``` shell
# truncate -s 100m bar.img
# mdconfig -a -t vnode -f bar.img
md0

# echo "super duper secret" > bar.pass
# dd if=/dev/random of=bar.key bs=64 count=1
# geli init -J bar.pass -K bar.key /dev/md0

# geli attach -j bar.pass -k bar.key /dev/md0
# dd if=/dev/random of=/dev/da2.eli bs=1m
# newfs /dev/md0.eli
# mount /dev/md0.eli /mnt
# echo "THIS IS ANOTHER MARKER." > /mnt/README2.txt
# umount /mnt
# geli detach /dev/md0.eli
# mdconfig -d -u 0
```

さて、このbar.imgを探索すれば、ファイル名(README2.txt)やその内容("THIS
IS ANOTHER MARKER.")を復元することができるのか？
できないのである。

``` shell
# strings bar.img | grep README
# strings bar.img | grep "THIS IS"
```

`file`で見てみても、foo.imgはUFS2のファイルシステムが入っていることが
示されるのに対して、bar.imgは(なんかわからんけど)データやで、としかわ
からない。

``` shell
# file foo.img bar.img
foo.img: Unix Fast File system [v2] (little-endian) <以下略>
bar.img: data
```

というわけで、GELIによる暗号化を行えば、ディスクデバイスを処分するとき
でも平文のデータが格納されているわけではない(らしい)ことがわかった。
実際にはパスフレーズや暗号鍵がわかると復号できてしまうのでこれらを一緒
に処分してはならないとか、強いパスフレーズ・暗号鍵を使うとか、いろいろ
考えることはあるけれども。

なお、２回目以降に暗号化ディスクを使う時は、`geli attach`して使えばよ
く、保護状態に戻すには`geli detach`すればよい。
(`newfs`や`geli attach`は初回だけ実行すればよい。)

``` shell
# mdconfig -a -t vnode -f bar.img
md0
# geli attach -j bar.pass -k bar.key /dev/md0
# mount /dev/md0.eli /mnt
# ls /mnt
.snap/       README2.txt
    :
# umount /mnt
# geli detach /dev/md0.eli
# mdconfig -d -u 0
```

## rc.conf, fstabへの統合

実際に運用する際には、保護状態の暗号化ディスクを、起動時にアタッチして
マウントし、電源断時にアンマウントして保護状態に戻す必要がある。
これは、rc.confとfstabの設定で可能。

ada0から起動しているFreeBSDシステムがあって、新たにディスクada1を追加
し、ディスク暗号化して使うケースを考える。

まず、ada1の初期化。
やっていることは先ほどのbar.imgの時と同じ。
`pwgen`を使ってパスフレーズを作っているので、さっきよりは強いパスフレー
ズになっているはず。

``` shell
# mkdir /etc/geli
# cd /etc/geli
# pwgen -y 32 1 > ada1.pass
# dd if=/dev/random of=ada1.key bs=64 count=1
# geli init -J ada1.pass -K ada1.key /dev/ada1
# geli attach -j ada1.pass -k ada1.key /dev/ada1
# dd if=/dev/random of=/dev/ada1.eli bs=1m
# newfs /dev/ada1.eli
# mount /dev/ada1.eli /mnt
# ls /mnt
    :
# umount /mnt
# geli detach /dev/ada1.eli
```

これをrc.confやfstabの設定からやってもらうには、以下のように設定すれば
よい。
(説明の都合上、マウントポイントを/mnt/a, /mnt/b, /mnt/c にしている。
あらかじめ`mkdir`しておいてほしい。)

``` shell
[/etc/rc.conf]
geli_devices="ada1.eli"
geli_ada1_flags="  -j /etc/geli/ada1.pass   -k /etc/geli/ada1.key"
```

``` shell
[/etc/fstab]
/dev/ada1.eli	/mnt/a		ufs	rw	2	2
```

GELIの設定の方は、`service geli start`や`service geli stop`で試す
ことができる。マウント処理の方は`(u)mount /mnt`でできる。

ada1が保護状態にあり、従ってマウントもされていない状態から、
GELI的にアタッチするには

- `service geli start`を実行すれば/dev/ada1.eliが生えてくる。
  - これは、下に示す`geli attach`のコマンドラインと同じであろう。
  - `service`では複数の設定がある場合には全部やっちゃうので使い分けて
    ほしい。
- これをマウントするのは`mount`で可能。
  fstabに設定があるので`mount /mnt/a`でできる。

``` shell
# service geli start
    OR
# geli attach -j /etc/geli/ata1.pass -k /etc/geli/ada1.key /dev/ada1

# mount /mnt/a
```

この状態からada1をアンマウントして保護状態に戻すには、

- `umount`すれば良い。
  - /etc/defaults/rc.confで`geli_autodetach="YES"`がデフォルト設定に
    なっているので、アンマウントすれば、GELI的にデタッチしてくれる。
	/etc/rc.d/geliから`geli attach`する時に ``-d`オプションが付いてい
    るということだと思う。
  - というわけで(`service geli stop`または`geli detach`をしなくても)
    /dev/ada1.eliは消えているはず。

``` shell
# umount /mnt/a
```

これで、システム起動時には自動的に/dev/ada1をGELI的にアタッチしてマウ
ントし、システム終了時には自動的にアンマウントしてGELI的デタッチをして
くれるはずである。








# cd /etc
# mkdir geli
# cd geli
# pwgen -y 32 1 > ada1.pass
# dd if=/dev/random of=ada1.key bs=64 count=1
1+0 records in
1+0 records out
64 bytes transferred in 0.000133 secs (480878 bytes/sec)


# geli init -s 4096 -J foo.pass -K foo.key /dev/md0

Metadata backup for provider /dev/md0 can be found in /var/backups/md0.eli
and can be restored with the following command:

	# geli restore /var/backups/md0.eli /dev/md0


# geli attach -j foo.pass -k foo.key /dev/md0
# ls -l /dev/md*
crw-r-----  1 root operator 0xa4 Mar 10 17:50 /dev/md0
crw-r-----  1 root operator 0xa7 Mar 10 17:51 /dev/md0.eli
crw-------  1 root wheel     0xa Mar 10 11:43 /dev/mdctl

# newfs /dev/md0.eli
/dev/md0.eli: 100.0MB (204792 sectors) block size 32768, fragment size 4096
	using 4 cylinder groups of 25.00MB, 800 blks, 3200 inodes.
	with soft updates
super-block backups (for fsck_ffs -b #) at:
 192, 51392, 102592, 153792

# ls -l /mnt
total 0
# mount /dev/md0.eli /mnt
# ls -l /mnt
total 8
drwxrwxr-x  2 root operator 512 Mar 10 18:00 .snap/

# echo "This is a marker." > /mnt/README.txt
# ls -l /mnt
total 16
drwxrwxr-x  2 root operator 512 Mar 10 18:00 .snap/
-rw-r--r--  1 root wheel     18 Mar 10 18:02 README.txt

# umount /mnt
# ls -l /mnt
total 0

# ls -l /dev/md*
crw-r-----  1 root operator 0xa4 Mar 10 17:50 /dev/md0
crw-r-----  1 root operator 0xa7 Mar 10 18:04 /dev/md0.eli
crw-------  1 root wheel     0xa Mar 10 11:43 /dev/mdctl
# geli detach /dev/md0.eli
# ls -l /dev/md*
crw-r-----  1 root operator 0xa4 Mar 10 17:50 /dev/md0
crw-------  1 root wheel     0xa Mar 10 11:43 /dev/mdctl

# mdconfig -d -u 0
[root@dreadnought gelitest]# ls -l /dev/md*
crw-------  1 root wheel 0xa Mar 10 11:43 /dev/mdctl

# file foo.img
foo.img: data
# strings foo.img | grep "This is a marker."
#

gpart create -s GPT /dev/md0.eli
gpart add -t freebsd-ufs /dev/md0.eli
gpart status /dev/md0.eli
gpart list /dev/md0.eli

newfs /dev/md0.elip1

mount -t ufs /dev/md0.elip1 /mnt

echo "This is a marker." > /mnt/README.txt
ls -l /mnt

umount /mnt

geli detach /dev/md0.eli
ls /dev/md*




