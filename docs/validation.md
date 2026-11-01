# 動作確認（2026年11月1日）

クリーンなoverlayで3パッケージのビルドに成功。`ros2 pkg prefix` は両vendorパッケージとも `/workspace/install/` 配下。元教材の削除・改名はしていない。

## 実走

同じ `patrol.world`、同じロボット初期位置で2回、人物なしの前進→箱手前の旋回回避→搭載カメラの人物連続検出→速度ゼロ・停止保持を確認した。実行ログの抜粋と集計は `validation/patrol/run{1,2}/`。人物座標やタイマーから停止を決めるコードはない。人物actorは固定位置でアニメーションする。

1回目は観測開始36.313秒で停止保持。停止に使った2画像のシミュレーションstampは17.963秒と18.363秒、信頼度0.8733 / 0.8057。停止後48秒以上観測し、停止3秒後以降のオドメトリ最大並進速度0.000903 m/s、最大角速度0.000872 rad/s。速度指令はゼロを保持した。

2回目は38.892秒で停止保持。判定画像stampは18.545秒と18.746秒、スコア0.8793 / 0.8837。停止後51秒以上観測し、停止3秒後以降の最大並進速度0.001823 m/s、最大角速度0.001340 rad/s。厳密な値は `validation/patrol/run2/summary.json` を参照。動画素材は `recordings/final2/camera.mp4`。ソフトウェア描画のため実時間よりシミュレーション進行は遅い。CPU推論時間は静止画事前検証と異なり同時実行の負荷を含む。

接触センサーによる無衝突判定は行っていない。壁すべてを巡回する長時間試験、他の人物モデル、実機、異なる計算機は未検証。

## 制御の確認

`validation/control/check_controller.py` で次を確認（結果JSONあり）。Gazeboでの障害注入試験とは区別する。

- 起動直後、推論結果なし、LiDAR受信途絶、画像・推論結果の受信途絶でゼロ指令。
- 無効なLaserScan値は停止、+infは測距上限として扱う。
- 1画像だけの検出と同じstampの再通知では停止を保持しない。人物なし画像で連続回数をリセット。
- 異なる2画像の連続検出で停止保持。その後人物なしでも再開しない。

モデル読み込み失敗はdetectorが例外をログに残し結果を配信しない実装であり、controllerの「結果なしで停止」を確認した。実走中のプロセス停止・カメラ停止・LiDAR停止を個別に注入する試験は未実施。通常終了時はcontrollerが通信を閉じる前にゼロ指令を送るよう実装。二重SIGINTにより後処理が中断する問題を修正し、`validation/control/check_shutdown.py` で入力なしの場合もcontroller・detectorがともに終了コード0になることを確認した（shutdown.json）。

## 実装中に判明した問題

- 物理刻みだけの設定では車体が飛び出す異常が発生。教材のODEソルバー設定（1ms、150反復、拘束設定）を用いて改善。失敗試行の録画は提出素材に使用しない。
- この環境では大きな画像のBEST_EFFORT購読が途切れた。配信に合わせてRELIABLE・KEEP_LAST 1に変更し、連続推論・2回の走行を確認。LiDARは小さなメッセージでBEST_EFFORT購読。
- 初期推論やCPU負荷で古くなった結果は配信せず、controllerは待機する。重み、640入力、0.5閾値は事前検証と同じ。

## トピック

実起動後に確認：画像 `/camera/image_raw` (sensor_msgs/Image)、LiDAR `/scan` (sensor_msgs/LaserScan) はRELIABLE・VOLATILE・depth 5配信。`/cmd_vel` (geometry_msgs/Twist) はcontrollerからRELIABLE配信、Gazebo差動駆動が購読。検出 `/person/result`、状態 `/patrol/state` はstd_msgs/String。注釈画像 `/person/annotated`。

## 残る提出作業

説明PDF（docs/report.pdf）と説明付き約110秒MP4（recordings/submission.mp4）を作成した。PDFの提出名と動画の最終タイトルには利用者のOmniCampusアカウント名またはIDが必要。公開GitHub、YouTubeアップロード、公開設定・個人情報の最終確認、OmniCampus送信は未実施。
