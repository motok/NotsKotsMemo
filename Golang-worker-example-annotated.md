# Go言語によるワーカー実装例（注釈付き）

## これは何？

- Go言語ではchannelと通信を用いて並列実行を「たやすく」書くことができる。
- でもそんなに「たやすく」はなかったので、[github:mefellows/golang-worker-example](https://github.com/mefellows/golang-worker-example)を頑張って追ってみた。
- 貴重な実装例を公開してくださったmefellowsさんに感謝いたします。また、本稿に錯誤や問題があったとしても当然のことながら私の責任であります。

## Golang-worker-exampleがやっていること

- 127.0.0.1:8000にHTTPサーバを建てて、リクエストを受け付ける。
- `curl -v -X POST "127.0.0.1:8000/work?delay=1s&name=foo`のようなリクエストが来たら、応答する。本番なら内部でいろいろ処理をやるはずだが、ここではダミーの`sleep`だけ。
- その内部処理をchannelを使った並列動作で、かつ、同時に走るgoroutine数を一定数に抑えながら実装した例である、ということであります。

## プログラムの流れ

- [main()](https://github.com/mefellows/golang-worker-example/blob/master/main.go)では、大雑把に言うと以下のことをやっている。
  - ディスパッチャ(StartDispatcher)の立ち上げ。
  - ジェネレータ(Collector)をHTTPサーバに登録。
  - HTTPサーバの立ち上げ(http.ListenAndServe)
- ディスパッチャ[StartDispatcher()](https://github.com/mefellows/golang-worker-example/blob/master/dispatcher.go)では
  - 「ワーカー待機列チャンネルWorkerPool」を作成。
  - 同時実行goroutine数の分の「ワーカworker」を作成(NewWorker)して実行開始(worker.Start)。
  - ディスパッチャ本体としては、「仕事分配チャンネルWorkQueue」から仕事を読み込めれば(work := <-WorkQueue)、「ワーカ待機列チャンネルWorkerPool」から「ワーカworker」を取り出してそこに「仕事work」を書き込む。
- NewWorker関数やその他の「ワーカworker」関連は主に[worker.go](https://github.com/mefellows/golang-worker-example/blob/master/worker.go)にあって、WorkRequestだけが[work.go](https://github.com/mefellows/golang-worker-example/blob/master/work.go)にある。
  - NewWorker関数ではWorker構造体を生成して返す。
  - worker.Start関数では、(準備のできたワーカ==自分が)「ワーカ待機列チャンネルWorkerPool」に「自分専用仕事受付チャンネルworker.Work」を書き込む。
  - ジェネレータ側でこのチャンネルに仕事を書き込む（後述）と、ワーカが取り出して仕事する(WorkRequest.Execute このWorkRequest構造体だけはwork.go側で定義されている)。
- ジェネレータ側は[collector.go](https://github.com/mefellows/golang-worker-example/blob/master/collector.go)に定義されている。
  - 「仕事分配チャンネルWorkQueue」を定義。
  - main関数から呼ばれるCollector関数では、最低限のHTTPリクエスト処理をやった後、WorkRequest.Executeに与える仕事処理関数(doFunc)を定義。ここではerrorとしてnilを返すだけ(あるいはなにか!nilを返せば処理失敗を模擬できる)だけ。
  - さらに「仕事work」(これはWorkRequest型)を作って「仕事分配チャンネルWorkQueue」に書き込む。

## 主要な部品

### ジェネレータ側で「仕事」を「仕事分配チャンネル」に書き込む

- まず[「仕事分配チャンネルWorkQueue」はジェネレータ(Collector)の冒頭で定義](https://github.com/mefellows/golang-worker-example/blob/9766bd3594f3b57898f21dadbac09a9f503bee53/collector.go#L10)されている。

  ```go
  // A buffered channel that we can send work requests on.
  var WorkQueue = make(chan WorkRequest, 100)
  ```

  - 「仕事分配チャンネルWorkQueue」がバッファ付き(100個)なのは、HTTPリクエストが殺到した時にここへ貯めることで取りこぼしを防ぐ工夫であろう。

- 「仕事分配チャンネルWorkQueue」には「仕事work」を入れたり出したりするわけだが、その[「仕事work」を表現するのがWorkRequest構造体](https://github.com/mefellows/golang-worker-example/blob/9766bd3594f3b57898f21dadbac09a9f503bee53/work.go#L3)。

  ```go
  type WorkRequest struct {
  	Execute func(config interface{}) error
  }
  ```

- ジェネレータ(Collector)がHTTPリクエストを受け取ると、[「仕事work」を生成](https://github.com/mefellows/golang-worker-example/blob/9766bd3594f3b57898f21dadbac09a9f503bee53/collector.go#L50)する。

  ```go
  work := WorkRequest{
  	Execute: doFunc,
  }
  ```

  - work.Executeに入る[doFuncは少し手前で定義](https://github.com/mefellows/golang-worker-example/blob/9766bd3594f3b57898f21dadbac09a9f503bee53/collector.go#L44)されている。まあダミーなので何もしないが、本当ならこれがHTTPリクエストに対する内部処理を行うことになる。config引数で動作を変更することも考慮されているのかな。

    ```go
    doFunc := func(config interface{}) error {
    	fmt.Sprintf("Doing shiit")
    	//return errors.New("Not a real problem..")
    	return nil
    }
    ```

  - できた「仕事work」は、[「仕事分配チャンネルWorkQueue」に書き込まれる](https://github.com/mefellows/golang-worker-example/blob/9766bd3594f3b57898f21dadbac09a9f503bee53/collector.go#L55)。

    ```go
    // Push the work onto the queue.
    WorkQueue <- work
    fmt.Println("Work request queued")
    ```

### ディスパッチャ側で「ワーカ」を「ワーカ待機列チャンネル」に書き込む

- [「ワーカ待機列チャンネルWorkerPool」はディスパッチャ(StartDispatcher)冒頭で定義](https://github.com/mefellows/golang-worker-example/blob/9766bd3594f3b57898f21dadbac09a9f503bee53/dispatcher.go#L5)されている。

  ```go
  type WorkerPoolType chan chan WorkRequest
  var WorkerPool WorkerPoolType
  func StartDispatcher(nworkers int) {
  	// First, initialize the channel we are going to but the workers' work channels into.
  	WorkerPool = make(WorkerPoolType, nworkers)
    :
  ```

  - 「仕事分配チャンネルWorkQueue」が「仕事」(WorkRequest)の<u>チャンネル</u>であったのに対して、「ワーカ待機列チャンネルWorkerPool」は「仕事」(WorkRequest)の<u>チャンネルのチャンネル</u>である点に注意。
  - 「ワーカ待機列チャンネルWorkerPool」は同時並列実行数(nworkers)個のバッファ付きであるが、こうすることで同時並列実行数(nworkers)個までの「ワーカーworker」が待機でき、かつ、余った「ワーカーworker」は書き込みブロックされる。
  - 一見ここで同時並列実行数(nworkers)以上の同時実行を防止しているようにも見えるが、もし手空きの「ワーカworker」があればどんどん「ワーカ待機列チャンネルWorkerPool」に入ってくるので防止できていない。
  - 結局、同時並列実行数(nworkers)を担保しているのは、後述の「ワーカworker」作成の際に同時並列実行数(nworkers)の分<u>しか</u>作らないことであると僕には思われる。ご意見ご感想ご教示歓迎です。

- 「ワーカ待機列チャンネルWorkerPool」には「ワーカworker」を入れたり出したりするわけだが、その[「ワーカ」を表現するのがWorker構造体](https://github.com/mefellows/golang-worker-example/blob/9766bd3594f3b57898f21dadbac09a9f503bee53/worker.go#L21)。

  ```go
  type Worker struct {
  	ID         int
  	Work       chan WorkRequest
  	WorkerPool chan chan WorkRequest
  	QuitChan   chan bool
  }
  ```

- ディスパッチャは「ワーカ待機列チャンネルWorkerPool」を定義した後、[同時並列実行数(nworkers)の分のワーカを作って(NewWorker)、実行開始(worker.Start)](https://github.com/mefellows/golang-worker-example/blob/9766bd3594f3b57898f21dadbac09a9f503bee53/dispatcher.go#L14)する。

  ```go
  // Now, create all of our workers.
  	for i := 0; i < nworkers; i++ {
  		fmt.Println("Starting worker", i+1)
  		worker := NewWorker(i+1, WorkerPool)
  		worker.Start()
  	}
  ```

- ワーカについては後述するとして、ディスパッチャは、「仕事work」があれば[「ワーカ待機列チャンネルWorkerPool」から「ワーカworker」を取り出し](https://github.com/mefellows/golang-worker-example/blob/9766bd3594f3b57898f21dadbac09a9f503bee53/dispatcher.go#L26)てその[「仕事work」を渡す](https://github.com/mefellows/golang-worker-example/blob/9766bd3594f3b57898f21dadbac09a9f503bee53/dispatcher.go#L29)。

  ```go
  go func() {
  		for {
  			select {
  			case work := <-WorkQueue:
  				fmt.Println("Received work requeust")
  				go func() {
  					worker := <-WorkerPool
  
  					fmt.Println("Dispatching work request")
  					worker <- work
  				}()
  			}
  		}
  	}()
  ```

### ワーカ作成と実行

- ディスパッチャが「ワーカworker」を作成するのに使った[NewWorker関数はworker.goの中で定義](https://github.com/mefellows/golang-worker-example/blob/9766bd3594f3b57898f21dadbac09a9f503bee53/worker.go#L10)されている。

  ```go
  // NewWorker creates, and returns a new Worker object. Its only argument
  // is a channel that the worker can add itself to whenever it is done its
  // work.
  func NewWorker(id int, workerQueue chan chan WorkRequest) Worker {
  	// Create, and return the worker.
  	worker := Worker{
  		ID:         id,
  		Work:       make(chan WorkRequest),
  		WorkerPool: workerQueue,
  		QuitChan:   make(chan bool)}
  
  	return worker
  }
  ```

  - NewWorker関数はWorker型の変数workerを作って返す。
  - 「自分専用仕事受付チャンネルworker.Work」にはWorkRequest型のチャンネルが入っていて、ここに「仕事work」が渡されると仕事をする(後述)。
  - 「自分専用仕事受付チャンネルworker.Work」は「仕事分配チャンネルWorkQueue」と同じ型のチャンネルであることに注意。
  - 「自分専用仕事受付チャンネルworker.Work」はそれぞれの「ワーカworker」に一つづつあるので、当該ワーカ専用の仕事受付チャンネルということになる。
  - worker.WorkerPoolには「ワーカ待機列チャンネルWorkerPool」が入っていて、準備ができた「ワーカworker」は自らの「仕事分配チャンネルwork.Work」をここへ送ることで「仕事work」の分配を受ける(後述)。

- 続いてディスパッチャは生成した「ワーカworker」の[Start関数を呼んで起動](https://github.com/mefellows/golang-worker-example/blob/9766bd3594f3b57898f21dadbac09a9f503bee53/worker.go#L28)する。

  ```go
  // This function "starts" the worker by starting a goroutine, that is
  // an infinite "for-select" loop.
  func (w Worker) Start() {
  	go func() {
  		for {
  			// Add ourselves into the worker queue.
  			w.WorkerPool <- w.Work
  
  			select {
  			case work := <-w.Work:
  				// Receive a work request.
  				work.Execute(nil)
  			case <-w.QuitChan:
  				// We have been asked to stop.
  				fmt.Printf("worker%d stopping\n", w.ID)
  				return
  			}
  		}
  	}()
  }
  
  ```

  - Start関数内では、まず[「自分専用仕事受付チャンネルworker.Work」を「ワーカ待機列チャンネルWorkerPool」に送る](https://github.com/mefellows/golang-worker-example/blob/9766bd3594f3b57898f21dadbac09a9f503bee53/worker.go#L34)。
  - [ディスパッチャがこれを取り出して](https://github.com/mefellows/golang-worker-example/blob/9766bd3594f3b57898f21dadbac09a9f503bee53/dispatcher.go#L26)、[「仕事work」を渡す](https://github.com/mefellows/golang-worker-example/blob/9766bd3594f3b57898f21dadbac09a9f503bee53/dispatcher.go#L29)と、その[「仕事work」を「自分専用仕事受付チャンネルworker.Work」から読み出して](https://github.com/mefellows/golang-worker-example/blob/9766bd3594f3b57898f21dadbac09a9f503bee53/worker.go#L37)、work.Execute関数を呼び出すことで仕事をする。

  ### 流れ図

  ```sequence
  participant client
  participant generator
  participant WorkQueue
  participant dispatcher
  participant WorkerPool
  participant worker
  
  client -> generator:HTTP Requests
  generator -> WorkQueue: work
  
  dispatcher -> worker: NewWorker()
  dispatcher -> worker: worker.Start()
  worker -> WorkerPool: worker.Work
  
  WorkerPool -> dispatcher: worker.Work
  WorkQueue -> dispatcher: work
  dispatcher -> worker: work
  ```

## まとめ

- [mefellowsさんのGolang-worker-example](https://github.com/mefellows/golang-worker-example)を例に採って、その構造を勉強させていただいた。実装例を公開していただいたことで手元で実際に動かすことができたので理解が深まった。ありがとうございました。
- 並列・並行処理は難しい...。