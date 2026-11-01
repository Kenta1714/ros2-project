# 人物を検出したら停止する巡回ロボット

ROS 2 Humble / Gazebo Classic 11 の Happy Mini を低速走行させ、LiDARで壁や箱を避け、搭載RGBカメラをYOLOv8nで認識する。人物を異なる2画像で連続検出したら停止を保持する。再開はプロセス再起動。

## 環境

教材の [Dockerイメージ](https://github.com/AI-Robot-Book-Humble/docker-ros2-desktop-ai-robot-book-humble) にある Ubuntu 22.04、ROS 2 Humble、Gazebo Classic 11.10.2 を使用。Python 3.10.12、NumPy 1.24.4、torch 2.6.0、ultralytics 8.3.74、cv_bridge、OpenCV、colcon が既存。GPU、APIキー、追加学習は不要。既存Python依存を一括更新しない。

## ビルド・起動

```bash
cd /workspace
bash scripts/download_model.sh
bash scripts/build.sh
bash scripts/run_demo.sh
```

スクリプトは `.bashrc` を読まず、継承したROS overlay関連変数を解除して `/opt/ros/humble` とこのリポジトリだけを読み込む。元教材のワークスペースは実行時に不要。モデルのSHA256は `f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36`。

VNCのXサーバーが必要。既定は `DISPLAY=:0`、`XAUTHORITY=/home/ubuntu/.Xauthority`。別環境では自身の認証ファイルを指定する。`xhost +` は不要。ソフトウェア描画を使用。既定のROS_DOMAIN_ID=68、Gazebo master=11368を他の実行と共用しない。同時に複数起動しない。

別の端末で表示・確認する場合：

```bash
cd /workspace
source scripts/clean_env.sh
source install/setup.bash
export ROS_DOMAIN_ID=68 GAZEBO_MASTER_URI=http://127.0.0.1:11368
export DISPLAY=:0 XAUTHORITY=/home/ubuntu/.Xauthority LIBGL_ALWAYS_SOFTWARE=1
gzclient
# 別端末で搭載カメラを表示
ros2 run rqt_image_view rqt_image_view /person/annotated
# 状態表示
ros2 topic echo /patrol/state
# ローカルパッケージの確認
ros2 pkg prefix turtlebot3_gazebo
ros2 pkg prefix turtlebot3_description
```

終了は起動端末でCtrl+C。controllerは終了時に可能な範囲で速度ゼロを送る。強制終了や通信断に対する実機安全装置ではない。

## 仕組み

- `/scan` の角度を `angle_min + index * angle_increment` から求め、前方±0.45 radと左右を比較。+infはrange_max、NaN等は除外。前方0.6 m未満で空いている側へ0.3 rad/sのその場旋回、通常0.08 m/s前進。旋回方向は1秒保持。
- `/camera/image_raw` の最新画像を別スレッドから推論。モデルは一度だけCPUで読み込み、640ピクセル入力、人物クラス0・信頼度0.5以上。画像購読はRELIABLE・深さ1とし、最新画像1枚だけを保持し、同一タイムスタンプを再処理しない。
- `/person/result` は画像stamp、シーケンス、人物有無、スコア、推論時間、画像受信からの経過秒をJSONで通知。人物なしも有効な結果として送信。画像が2秒以上古い場合は送信しない。
- controllerは別プロセスで10 Hz制御。LiDAR 1.5秒・結果3秒の受信途絶、初期化中、有効な前方/左右観測なしでは停止。監視は単調時刻。人物を2画像で連続検出したら `/cmd_vel` をゼロにして保持。停止条件に人物座標や経過時間を使わない。
- `/person/annotated` に検出枠・スコア、`/patrol/state` に状態を配信。人物actorは固定位置でアニメーションを再生。LiDAR用の静的collisionを同位置に追加した。

## 動画と証拠

観測用（制御しない）：

```bash
# 上記と同様に環境を設定した端末
python3 scripts/observe.py --output recordings/run1 --seconds 120
```

`events.jsonl` に状態、検出、速度指令、オドメトリ、`camera.mp4` に注釈カメラと状態を保存する。worldとは別の固定観察カメラがGazebo全体像を撮影し、搭載カメラと並べて記録する。観察カメラは制御に使用しない。目的・AI方式・工夫・限界を加えて1〜3分MP4にする。録画・ビルド・重み・ログ・課題PDFはGit対象外。検証証拠は `validation/` に保存する。

## 提出

実施結果は `docs/validation.md`、レポート原稿は `docs/report.md` を参照。公開・アップロード・OmniCampus送信は行わない。提出時にpublic GitHub、1〜3分動画、説明PDFを用意する。PDF名は `説明資料_PAI最終課題_omnicampusアカウント名.pdf`、動画タイトルは `PAI最終課題_omnicampusアカウント名`（個人名ならIDの利用を確認）。成果物の個人情報や通知の映り込みを確認する。

限定した環境・1種類の人物モデルでの課題。部屋全体の探索、一般的な認識性能、無衝突、実機の安全性は保証しない。障害物回避はルール制御。出典とライセンスは `THIRD_PARTY.md`。

## この環境で作成した提出素材

- `recordings/submission.mp4`：説明付き約110秒、1280×720、再生速度変更なし。Git対象外なので動画サービスへ別途提出する。
- `docs/report.pdf`：日本語説明資料（1ページ）。提出時に指定のアカウント名またはIDを付けたファイル名へ変更する。
- `validation/patrol/run1/` と `run2/`：2回の実走の状態・検出・速度記録。

素材の再生成は `python3 scripts/export_video.py`、PDFは `python3 scripts/export_report.py`。動画生成はffmpegとPillow、PDFはReportLabとTakaoフォントを使う（この環境には導入済み、ロボットの実行には不要）。動画はOmniCampusアカウント名が未指定なので汎用タイトルで作成した。YouTube投稿時に指定形式のタイトルを設定する。
