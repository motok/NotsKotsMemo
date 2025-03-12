# UFS on GELI

{{_TOC_}}

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
MARKER.")を復元することができるのか？
(DFIRとかDisk Forensicsとかを持ち出すまでもなく)できるのである。
まあ、マウントすれば読めるしね。

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
  - 運用上パスフレーズを変更したい時でも暗号鍵は変わらないのでディスク
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
に処分してはならないとか、強いパスフレーズ・暗号鍵を使おうよとか、
いろいろ考えることはあるけれども。

なお、２回目以降に暗号化ディスクを使う時は、`geli attach`して
`mount`して使えばよく、保護状態に戻すには`umount`して
`geli detach`すればよい。
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

## GPTパーティションとの関係

上のada1の場合には、ディスクデバイスに直接にファイルシステムを載せたが、
パーティションを切りたい場合もあるだろう。
ということで、

- (ada1) 上述のディスクデバイスに直接にファイルシステムを載せる場合に
  加えて、
- (ada2) ディスクデバイスにGPTのパーティションを切って、その中のスライスを
  暗号化する場合と、
- (ada3) ディスクデバイス全体を暗号化して、その上にGPTのパーティションを
  切る場合

についてやってみよう。

/etc/rc.confと/etc/fstabの設定としては、以下のものでよい。

``` shell
[/etc/rc.conf]
geli_devices="ada1.eli ada2p1.eli ada3.eli"
geli_ada1_flags="  -j /etc/geli/ada1.pass   -k /etc/geli/ada1.key"
geli_ada2p1_flags="-j /etc/geli/ada2p1.pass -k /etc/geli/ada2p1.key"
geli_ada3_flags="  -j /etc/geli/ada3.pass   -k /etc/geli/ada3.key"
```

``` shell
[/etc/fstab]
/dev/ada1.eli   /mnt/a          ufs     rw      2       2
/dev/ada2p1.eli /mnt/b          ufs     rw      2       2
/dev/ada3.elip1 /mnt/c          ufs     rw      2       2
```

ada2とada3用のパスフレーズと暗号鍵の作り方はada1と同様なので割愛する。

ada2の初期化は次の通り。GPTのパーティション上にスライスを作成し、その
スライスを暗号化して使用するパターン。

- `gpart create`でGPTのパーティションを作成
- `gpart add`でスライスを追加。
  ここではタイプとしてfreebsd-ufsを指定しているが、正しくはgeliとか
  なんとかにしないといけない気がする。
  `man gpart`で見た限りだと適当なものがないし、
  freebsd-ufs指定で動いているので、これにしておく。
- お馴染みの`geli init`と`geli attach`。
  デバイスとしてada2p1スライスを指定している点に注目。
- あとは、マウントして使えばよい。
- 後片付けも、お馴染みの `umount`と`geli detach`。

``` shell
# gpart create -s GPT /dev/ada2
# gpart add -t freebsd-ufs -s 100M /dev/ada2

# geli init -J /etc/geli/ada2p1.pass -K /etc/geli/ada2p1.key /dev/ada2p1

# geli attach -j /etc/geli/ada2p1.pass -k /etc/geli/ada2p1.key /dev/ada2p1
# mount /dev/ada2p1.eli /mnt/b
# ls /mnt/b
    :
# umount /mnt/b
# geli detach /dev/ada2p1.eli
```

ada3の初期化は次の通り。ada3全体を暗号化して、その上にGPTの
パーティションを作成するパターン。

- `geli init`でada3全体を暗号化し、`geli attach`でアタッチする。
  これはada1の時と同様。
- アタッチで生えてきた/dev/ada3.eliに対して`gpart create`でGPTのパーティ
  ションを作成し、`gpart add`でスライスを追加する。
  デバイス名に.eliが付いている点に注目。
- あとは、マウントして使えばよい。
- 後片付けも、お馴染みの `umount`と`geli detach`。


``` shell
# geli init -J /etc/geli/ada3.pass -K /etc/geli/ada3.key /dev/ada3
# geli attach -j /etc/geli/ada3.pass -k /etc/geli/ada3.key /dev/ada3

# gpart create -s GPT /dev/ada3.eli
# gpart add -t freebsd-ufs -s 100M /dev/ada3.eli

# mount /dev/ada3.elip1 /mnt/c
# ls /mnt/c
    :
# umount /mnt/c
# geli detach /dev/ada3.eli
```


## まとめ

ということで、FreeBSD 14.2で、GELIによるディスクの暗号化を行い、システ
ム起動時・終了時に自動的に処理されるように設定を行なった。

実際に運用する場合には、スワップパーティションの準備やスライス分割して
使う場合などが頭をよぎるので、
「ディスク全体を暗号化して、その上にGPTパーティションを作成する」
パターンが使いやすいかなぁ。

スワップの暗号化やZFSとの統合、暗号化した場合のパフォーマンス低下がど
の程度か、などについては、将来の課題として保留しておく。

(2025-03-12)
