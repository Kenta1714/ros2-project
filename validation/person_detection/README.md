# Gazebo人物検出の事前検証

2026年11月1日にこのコンテナで実行。**事前学習済みYOLOv8nで、Gazebo内の人物を認識できたため、人物検出時に停止する巡回案を採用する。**

ここで確認したのは静止ロボットのカメラ画像からの人物検出まで。巡回走行、連続検出による停止、移動中のカメラ、実機の安全性は未検証。

## 結果

人物検出の判定閾値は0.5。画像を合成せず、Gazebo RGBセンサーの `sensor_msgs/Image` をそのまま保存して推論した。

| 条件 | 画像数 | 人物検出 | 信頼度 |
| --- | --- | --- | --- |
| 独立カメラ・後ろ姿・3 m | 3 | 3/3 | 0.8847 / 0.9202 / 0.9141 |
| 独立カメラ・人物なし | 1 | 0/1 | 検出なし |
| 元の搭載カメラ・人物3 m | 1 | 1/1 | 0.5355（車体の映り込みあり） |
| 修正後の搭載カメラ・正面3 m | 1 | 1/1 | 0.9231 |
| 修正後の搭載カメラ・横向き4 m | 1 | 1/1 | 0.9256 |
| 修正後の搭載カメラ・人物なし | 1 | 0/1 | 検出なし |
| 最終版スクリプトで正面3 mを再実行 | 1 | 1/1 | 0.9213 |

採用判断の主な証拠：

- [正面3m・元画像](results/onboard_fixed_3m/frame_00.png)
- [正面3m・検出枠](results/onboard_fixed_3m/frame_00_detected.jpg)
- [横向き4m・検出枠](results/onboard_fixed_side_4m/frame_00_detected.jpg)
- [人物なし・検出結果](results/onboard_fixed_empty/frame_00_detected.jpg)
- 詳細はそれぞれのディレクトリの `results.json`。全検証ケースのJSON・元画像も保存した。

信頼度は正解率ではない。限定した照明・距離・1種類の人物モデルでの確認であり、一般の人や任意の向きへの性能を保証しない。

修正後の人物あり画像（再実行を含む3画像）のCPU推論はウォームアップ後0.1241〜0.2491秒/枚。推論前にGazeboを停止しており、同時実行中のFPSや停止遅延の測定ではない。画像取得・起動・モデル読み込み時間も含まない。

## カメラの調整と検証条件

- Gazebo標準の `file://media/models/walk.dae` を使用。人物の位置は固定で、骨格の歩行アニメーションを再生している。
- 初めにHappy Miniと同じ640×480・水平画角1.085595 radの独立カメラで検証し、続いて実際のHappy Miniモデルのカメラを使用した。
- 元のモデルではカメラ関連リンクに明示的なposeがなく、車体が映り込んだ。
- `assets/turtlebot3_happy_mini/model_camera_fixed.sdf` は `model.sdf` の派生版。`camera_link` と `camera_rgb_optical_frame` のlink poseを `0.08 0 1.03 0 0 0` に設定した。検証用のモデル原点z=0.01を含めカメラ高さは1.04 m。
- 撮影時だけモデルをstaticにし、モータープラグイン・LiDAR・IMUを無効化、カメラ更新を2 Hzにした。モデルの一部に重みを追加したり、人物を画像に貼り付けたりはしていない。
- 静止画取得はCPU描画・エミュレーション環境で遅くなる場合があった。人物なし画像を3枚待った試行が時間切れになったため、1枚の実画像で比較した。複数の異なるフレームを用いた停止判定は今後の確認項目。
- 検証用のGazebo masterは11367番ポート、ROS_DOMAIN_IDは67。既存のGazeboへ接続せず、撮影後に自分のサーバーを終了する。ポート使用中はエラーにする。

## 再実行

このDockerイメージに入っているROS 2 Humble、Gazebo Classic、Python 3.10、NumPy、OpenCV、torch、ultralyticsを使用する。新規インストールやHFトークンは不要。VNCのXサーバー `:0` が動いている状態で実行する。

```bash
cd /workspace
source /opt/ros/humble/setup.bash

# 初回のみ、公式配布の小型重みを取得する。
mkdir -p validation/person_detection/cache
curl -fL --retry 2 \
  https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt \
  -o validation/person_detection/cache/yolov8n.pt

# 調整したロボット搭載カメラ・正面3m。
python3 validation/person_detection/validate.py \
  --weights validation/person_detection/cache/yolov8n.pt \
  --robot-model validation/person_detection/assets/turtlebot3_happy_mini/model_camera_fixed.sdf \
  --distance 3 --yaw 3.14159265 --frames 1 \
  --output /tmp/pai-person-recheck
```

横向き4mは `--distance 4 --yaw 1.57079633`、人物なしは `--no-person` に変更する。異なる条件を同じ出力ディレクトリへ混在させず、各条件に別の `--output` を指定する。

実際の停止判定を検証するときは、最新画像を複数フレーム受信し、その画像が重複していないことも確認する。本スクリプトは停止制御を行わない。

取得済み画像に対する推論だけを再実行する場合は、同じ条件・出力先で `--infer-only` を追加する。付属の証拠を保持するため、再確認には新しい出力先を使うことを推奨する。出力先には元画像、検出枠付き画像、world、JSON、ログが保存される。

## バージョン・重み

- Gazebo Classic 11.10.2、ソフトウェア描画llvmpipe。
- Ultralytics 8.3.74、PyTorch 2.6.0、NumPy 1.24.4。
- 重みはYOLOv8n COCO事前学習済み。ローカルのキャッシュはGit対象外で、上記URLから再取得する。
- 重みのSHA256：`f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36`
- JSONには使用重みと元画像のSHA256を記録した。

## 出典

- ロボットモデル：[AI-Robot-Book-Humble/turtlebot3_happy_mini](https://github.com/AI-Robot-Book-Humble/turtlebot3_happy_mini)。教材の `turtlebot3_gazebo/models/turtlebot3_happy_mini` からコピー。元モデルと変更版を保存し、LICENSEとNOTICEは `assets/` に保持した。
- 人物モデル：Gazebo標準同梱の `walk.dae`。ベースイメージに含まれるGazebo資産を参照する。[actorの公式説明](https://classic.gazebosim.org/tutorials?tut=actor)。
- 検出モデル：[Ultralytics YOLOv8](https://docs.ultralytics.com/models/yolov8/)、重みは公式GitHub Releases。使用するコード・重みのライセンス表記と利用条件を保持・確認して提出する。

本実装でvendorパッケージへ資産を移すときは、同じモデルを重複して提出せず、本スクリプトのパスと再実行手順も合わせて更新する。

本実装に合わせ、メッシュは `src/vendor/turtlebot3_gazebo/models/turtlebot3_happy_mini/` に統合した。比較用2種類のSDFはassetsに保持し、validate.pyがメッシュURIをvendorのファイルへ解決するため、同じ再実行コマンドが使用できる。
