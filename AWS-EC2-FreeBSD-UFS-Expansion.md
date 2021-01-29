# AWS EC2上のFreeBSDでディスク拡張する

## これは何？

* AWS EC2にあるFreeBSD12.2のノードでディスク領域が足りなくなってきたので拡張した。
  * EBS gp2 10GB -> 20GB
* その手順を自分のために覚え書く。
* といっても、[serverfaultでのありがたい教え](https://serverfault.com/questions/482213/understanding-disk-space-on-ec2-freebsd-instance)に従っただけなので、そちらを見るほうが正しい。

## 最初の状態

* 10GBの/ (root)が一個だけあって、他には/bootだけという男前なパーティショニング。

* AWS Consoleから闇雲にディスクのサイズ拡大をしてノードをrebootしてみたが、当然それだけで完了するほど世の中は甘くない。

* ada0の(AWS EBS的)ボリュームは20GBになったようだが、gptは追随していないどころかCORRUPTとか言っているし、UFS的に見ても拡張されてはいない。

  ```shell
  # gpart show
=>       3  20971509  ada0  GPT  (20G) [CORRUPT]
         3       116     1  freebsd-boot  (58K)
       119  20971393     2  freebsd-ufs  (10G)
  ```

  ```shell
  # df -m
  Filesystem      1M-blocks Used Avail Capacity  Mounted on
  /dev/gpt/rootfs      9905 8496   616    93%    /
  devfs                   0    0     0   100%    /dev
  ```
  
* gptをrecoverしてみたら、CORRUPTとは言われなくなったが空き領域が10GB分できただけでdfから見ると何も変わっていない。

  ```shell
  # gpart recover ada0
  ada0 recovered
  
  # gpart show
  =>       3  41943029  ada0  GPT  (20G)
           3       116     1  freebsd-boot  (58K)
         119  20971393     2  freebsd-ufs  (10G)
    20971512  20971520        - free -  (10G)
  ```

  

## ディスクのやりくり

* ここで慌てて情報を探して上にも書いた[serverfaultでのありがたい教え](https://serverfault.com/questions/482213/understanding-disk-space-on-ec2-freebsd-instance)を発見。これに従うことにする。

* AWS Consoleから、現ボリューム(上のada0)のスナップショットを作成

* そのスナップショットを元に新ボリュームを作成

* ノードをshutdown

* 現ボリュームはそのままでノードに新ボリュームをアタッチする。新ボリュームはAWS Consoleでは/dev/sdfとしてアタッチすることに。

* ノードを開始してログイン

* FreeBSDから見ると、現ボリューム(一本目のディスクなのでada0として認識)に加えて、新ボリュームをxbd5として認識している。

  ```shell
  # gpart show
  =>       3  41943029  ada0  GPT  (20G)
           3       116     1  freebsd-boot  (58K)
         119  20971393     2  freebsd-ufs  (10G)
    20971512  20971520        - free -  (10G)
  
  =>       3  20971509  xbd5  GPT  (20G) [CORRUPT]
           3       116     1  freebsd-boot  (58K)
         119  20971393     2  freebsd-ufs  (10G)
  ```

* スナップショットを撮ったタイミングの関係でCORRUPT状態なので回復させる。

  ```shell
  # gpart recover xbd5
  xbd5 recovered
  
  # gpart show
  =>       3  41943029  ada0  GPT  (20G)
           3       116     1  freebsd-boot  (58K)
         119  20971393     2  freebsd-ufs  (10G)
    20971512  20971520        - free -  (10G)
  
  =>       3  41943029  xbd5  GPT  (20G)
           3       116     1  freebsd-boot  (58K)
         119  20971393     2  freebsd-ufs  (10G)
    20971512  20971520        - free -  (10G)
  ```

## GPT的拡張

* ada0はこのままにしておいてxbd5側を変更することで、最悪の場合でもada0が残るように作業する。

* xbd5の2番スライス(上ではfreebsd-ufsタイプのxbd5p2)をgpart的に20GBに拡張する。サイズが大きすぎたので少し小さくして二度目の試みで成功。

  ```shell
  # gpart resize -i 2 -s 20G xbd5
  gpart: size '41943040': Invalid argument
  
  # gpart resize -i 2 -s 20400M xbd5
  xbd5p2 resized
  [root@DaSeinRed0 moto]# gpart show
  =>       3  41943029  ada0  GPT  (20G)
           3       116     1  freebsd-boot  (58K)
         119  20971393     2  freebsd-ufs  (10G)
    20971512  20971520        - free -  (10G)
  
  =>       3  41943029  xbd5  GPT  (20G)
           3       116     1  freebsd-boot  (58K)
         119  41779200     2  freebsd-ufs  (20G)
    41779319    163713        - free -  (80M)
  ```

## UFS的拡張

* 新ボリューム(xbd5)の２番スライス(xbd5p2)をUFS的に拡張。

  ```shell
  # growfs xbd5p2
  It's strongly recommended to make a backup before growing the file system.
  OK to grow filesystem on /dev/xbd5p2 from 10GB to 20GB? [yes/no] yes
  super-block backups (for fsck_ffs -b #) at:
   21798272, 23080512, 24362752, 25644992, 26927232, 28209472, 29491712,
   30773952, 32056192, 33338432, 34620672, 35902912, 37185152, 38467392,
   39749632, 41031872
  ```

* 拡張したxbd5p2を確認。しめしめ。

  ```shell
  # mount -r /dev/xbd5p2 /mnt
  
  # df -m 
  Filesystem      1M-blocks Used Avail Capacity  Mounted on
  /dev/gpt/rootfs      9905 8496   616    93%    /
  devfs                   0    0     0   100%    /dev
  /dev/xbd5p2         19751 8496  9674    47%    /mnt
  
  # umount /mnt
  ```

## ボリューム入れ替え

* ここで、ノードをshutdownして、AWS Consoleで現ボリューム(上でada0としてみえているもの)をデタッチし、新ボリューム(同、xbd5)を一本目のディスクとしてアタッチする。
* 普通に新ボリュームをアタッチしに行くと/dev/sdfにアタッチすることになるので、ここで/dev/ada0を指定しなければならない。
* ノードを開始して確認作業へ。

## 確認作業

* GPT的には先程と同じく拡張済の状態。

  ```shell
  # gpart show
  =>       3  41943029  ada0  GPT  (20G)
           3       116     1  freebsd-boot  (58K)
         119  41779200     2  freebsd-ufs  (20G)
    41779319    163713        - free -  (80M)
  ```

* UFS的にも拡張されたことを確認。（さっきxbd5p2をマウントして見てたけどね）

  ```shell
  # df -m 
  Filesystem      1M-blocks Used Avail Capacity  Mounted on
  /dev/gpt/rootfs     19751 8496  9674    47%    /
  devfs                   0    0     0   100%    /dev
  ```

* これで作業完了。
* (2021/Jan/29頃書いた)



