# FreeBSD 15 gpart/zpool/zfs

## これは何？

- たまたまいくつかの SSD や HDD を初期化することがあったので、その備忘録。
- OS は FreeBSD 15.1-RELEASE-p5
- デバイスは次の通り。nda[01] は M.2 SSD で、ada1 は SATA SSD、ada2 は SATA HDD。

  | dev  | model | capacity | interface | note |
  | ---- | ----- | -------- | --------- | ---- |
  | nda0 | Apacer AS2280P4X | 2 TB | M.2 | PCIe Gen3x4, RW: 2100/1700 MB/s |
  | nda1 | Apacer AS2280P4X | 2 TB | M.2 | 同上 |
  | ada1 | TOSHIBA THNSN9240GESG | 240 GB | SATA 3.0 | 6 Gbps |
  | ada2 | Hitachi HDT725050VLA360 | 500 GB | SATA 300 | 3 Gbps 7200 github markrpm |

## gpart でパーティションテーブルを扱う

- 現状のパーティションテーブルを表示する。
  ``` shell
  # gpart show nda0 nda1 ada1 ada2 
  =>        40  4000797280  nda0  GPT  (1.9T)
	    40  4000797280     1  freebsd-ufs  (1.9T)

  =>        40  3907029088  nda1  GPT  (1.8T)
	    40  3907029088     1  freebsd-ufs  (1.8T)

  =>       40  468862048  ada1  GPT  (224G)
	   40  468862048        - free -  (224G)

  gpart: No such geom: ada2.
  ```
  - nda[01], ada[01] の現状のパーティションテーブルを表示した。
    nda[01] にはそれぞれ１個づつ freebsd-ufs 型のパーティションが定義されているが、
    ada1 ではパーティションテーブルは定義してあってもパーティションはなく、
    ada2 に至っては、パーティションテーブルそのものがない状態である。
  - これらは以前に使っていた時の残骸なので、一旦全パーティションテーブルを削除して
    新たに作り直すことにする。

- 現状のパーティションテーブルを一旦破壊する。
  - 必要なデータが残っている場合は別の場所へバックアップしておくこと。
    でないとデータが失われる。
  - nda0 で、パーティションを削除してからパーティションテーブルも削除するのは
    こんな感じ。
  ``` shell
  # gpart show nda0
  =>        40  4000797280  nda0  GPT  (1.9T)
	    40  4000797280     1  freebsd-ufs  (1.9T)

  # gpart delete -i 1 nda0
  nda0p1 deleted

  # gpart show nda0
  =>        40  4000797280  nda0  GPT  (1.9T)
	    40  4000797280        - free -  (1.9T)

  # gpart destroy nda0
  nda0 destroyed

  # gpart show nda0
  gpart: No such geom: nda0.
  ```
- 更地になった nda0 にパーティションテーブルとパーティションを作成するには、
  こんな感じ。
  ``` shell
  # gpart create -s gpt nda0
  nda0 created

  # gpart show nda0
  =>        40  4000797280  nda0  GPT  (1.9T)
	    40  4000797280        - free -  (1.9T)

  # gpart add -t freebsd-zfs -a 1m nda0
  nda0p1 added

  # gpart show nda0
  =>        40  4000797280  nda0  GPT  (1.9T)
	    40        2008        - free -  (1004K)
	  2048  4000794624     1  freebsd-zfs  (1.9T)
    4000796672         648        - free -  (324K)
  ```
  - `gpart add` に与えたオプション `-a 1m` は、作成するパーティションを
    1 MiB アラインメントに沿うようにするもの。
    最近の SSD では内部的に 4 kiB 〜 16 kiB の単位で読み書きしていて、消去の
    場合は「ブロック」(1 MiB 〜 数 MiB) の単位で消去するらしい。
    で、消去が複数ブロックに跨るとそれだけ SSD への読み書きが増えることになり、
    SSD の寿命に悪影響を及ぼすとのこと。
    なので、パーティションの境界を 1 MiB アラインメントに沿うようにしておくことで、
    なるべく消去対象ブロックを少なくする作戦であるようだ。
    上の例でもパーティションの前後に free 領域ができていてもったいない気もするが、
    これが今のベストプラクティスであるとのこと。
    既存パーティションを表示したときにはなかった "- free -" の領域に注目されたい。

- 上では、`gpart add` でパーティションサイズを指定しなかったので、可能な
  最大サイズで作成された。サイズを指定するなら `-s 10G` のように指定することが
  できる。こうすることで、複数のパーティションを作成することができる。
  ``` shell
  # gpart show ada2
  gpart: No such geom: ada2.

  # gpart create -s gpt ada2
  ada2 created

  # gpart add -t freebsd-ufs -a 1m -s 30G ada2
  ada2p1 added
  # gpart add -t freebsd-swap -a 1m -s 16G ada2
  ada2p2 added
  # gpart add -t freebsd-zfs -a 1m -s 130G ada2
  ada2p3 added
  # gpart add -t freebsd-zfs -a 1m -s 130G ada2
  ada2p4 added
  # gpart add -t freebsd-zfs -a 1m -s 130G ada2
  ada2p5 added
  # gpart add -t freebsd-zfs -a 1m  ada2
  ada2p6 added

  # gpart show ada2
  =>       40  976773088  ada2  GPT  (466G)
	   40       2008        - free -  (1004K)
	 2048   62914560     1  freebsd-ufs  (30G)
     62916608   33554432     2  freebsd-swap  (16G)
     96471040  272629760     3  freebsd-zfs  (130G)
    369100800  272629760     4  freebsd-zfs  (130G)
    641730560  272629760     5  freebsd-zfs  (130G)
    914360320   62412800     6  freebsd-zfs  (30G)
    976773120          8        - free -  (4.0K)
  ```

## zpool で ZFS プールを作成する

- 単純に１個のパーティションに ZFS プールを作成する。
  ``` shell
  # gpart show ada1
  =>       40  468862048  ada1  GPT  (224G)
	   40  468862048     1  freebsd-zfs  (224G)

  # zpool create -o ashift=12 -m none -m none singlepool ada1p1

  # zpool list
  NAME         SIZE  ALLOC   FREE  CKPOINT  EXPANDSZ   FRAG    CAP  DEDUP    HEALTH  ALTROOT
  singlepool   222G   492K   222G        -         -     0%     0%  1.00x    ONLINE  -

  # zpool get ashift singlepool
  NAME        PROPERTY  VALUE   SOURCE
  singlepool  ashift    12      local
  ```
  - オプション `-o ashift=12` は、このプールがセクターサイズ 4 kiB であるように
    設定している。昔は 512 kiB セクターが普通だったけど、今どきは 4 kiB かそれ以上
    らしい。LBA でもセクター番号が溢れるのでセクターサイズを大きくする必要があったはず。
  - オプション `-m none` を指定しない時は、/singlepool にこのプールをマウントする。
    指定すると、マウントポイントを「なし」と指定したので、マウントされない。
    自分しか使わないホストだったらデフォルトのままでも良いような気もするが、複数ユーザが
    使うなら権限管理が必要になって面倒だからマウントさせないというのもアリかな。
    でも、そうするとデータセット使用時にはマウントしないとダメかも。



1. マウントポイントを指定するオプション（-o mountpoint=...）

ZFSでは、データセット作成時に -o mountpoint=/パス を指定することで、任意の場所にマウントできます。
今回は「自動マウントはさせない（canmount=noauto）」というご要望ですので、以下のように組み合わせて指定します。
bash
# 例：プール「nvme_pool0」の中に、自動マウント無効・マウント先指定でデータセットを作成
zfs create -o mountpoint=/mnt/secure_nvme0 -o canmount=noauto nvme_pool0/mydata
コードは注意してご使用ください。
• 仕組み: このコマンドを実行すると、デフォルトのマウント先として /mnt/secure_nvme0 がデータセットに記録されますが、canmount=noauto が効いているため、この時点ではまだマウントされません（ディレクトリも自動作成されません）。
• 利用時: 実際に使いたいときに zfs mount nvme_pool0/mydata とだけ実行すれば、自動的に先ほど設定した /mnt/secure_nvme0 にマウントされます。

2. ZFSデータセットで強く推奨されるその他のオプション

データセットを作成する際、同時に設定しておくべき推奨オプションです。これらはすべて zfs create 時に -o オプション=値 の形で複数同時に指定できます。

① atime=off （すべてのSSD/HDDで強く推奨）

ファイルが「読み込まれた日時（アクセス日時）」をディスクに書き込む機能を無効にします。
• 理由: デフォルト（on）のままだと、ファイルを読み込むだけでもディスクへの書き込み（シーク）が発生します。これを off にすることで、無駄な書き込みを大幅に減らし、SSDの寿命延命とディスク全体のパフォーマンス向上に直結します（大半のアプリケーションで off にしても問題ありません）。

② compression=lz4 （すべてのSSD/HDDで強く推奨）

ZFSの高速な圧縮アルゴリズム（LZ4）を有効にします。
• 理由: 現代のCPUにとってLZ4の圧縮・展開処理は非常に軽量です。ディスクに書き込むデータ量が減るため、結果としてディスクの読み書き速度が実質的に向上（ブースト）します。また、SSDへの総書き込み量（TBW）を減らす効果もあります。

③ atime=off 以外のHDD向け調整（必要に応じて）

もしHDD（ada2）に、OSのパッケージや小さなファイル（ソースコードなど）ではなく、大きなメディアファイル（動画、音楽、バックアップイメージ等）をメインに保存する場合、以下のオプションも効果的です。
• recordsize=1M （大容量ファイルを置くデータセットのみ）
	• ZFSがデータを扱うブロックサイズを、デフォルトの128kBから1MBに拡大します。HDDのヘッドが動く回数が減り、シーケンシャルな読み書きが大幅に高速化します。

💡 推奨オプションを反映した実際の作成コマンド例

これらを踏まえると、データセット作成コマンドは以下のようになります。
bash
# NVMe SSD / SATA SSD 用のデータセット作成例
zfs create -o mountpoint=/mnt/ssd0 -o canmount=noauto -o atime=off -o compression=lz4 nvme_pool0/mydata
zfs create -o mountpoint=/mnt/ssd1 -o canmount=noauto -o atime=off -o compression=lz4 nvme_pool1/mydata
zfs create -o mountpoint=/mnt/sata0 -o canmount=noauto -o atime=off -o compression=lz4 sata_ssd0/mydata
zfs create -o mountpoint=/mnt/sata1 -o canmount=noauto -o atime=off -o compression=lz4 sata_ssd1/mydata

# HDD 用のデータセット作成例（大容量メディア用途を想定して recordsize も追加）
zfs create -o mountpoint=/mnt/hdd0 -o canmount=noauto -o atime=off -o compression=lz4 -o recordsize=1M hdd_pool0/mydata
コードは注意してご使用ください。
今回は各プールの中に「mydata」というデータセットを1つ作る例にしていますが、用途（例：データベース用、バックアップ用など）に応じてさらにデータセットを細かく分ける予定はありますか？ 必要であれば用途別の推奨値（recordsize の微調整など）もご提案できます。
