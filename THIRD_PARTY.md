# 出典と利用条件

- `src/vendor/` は [AI-Robot-Book-Humble/turtlebot3_happy_mini](https://github.com/AI-Robot-Book-Humble/turtlebot3_happy_mini) の `turtlebot3_gazebo` と `turtlebot3_description` のコピー。Apache-2.0。上位の LICENSE、NOTICE を同ディレクトリに保持。教材・ROBOTIS の著作権表示を維持する。worldのODEソルバー設定も教材worldを参考にした。変更は Happy Mini SDF のカメラ関連2リンクの pose、カメラ更新頻度5 Hz、camera_name/frame_name の明示。
- 独自部分：`src/person_stop_patrol/`、`scripts/`、world、文書。AGPL-3.0-or-later。第三者ファイルには元のライセンスが適用される。
- YOLOv8n：Ultralytics 8.3.74 / COCO事前学習済み重み。[公式配布](https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt)。[公式ライセンス案内](https://www.ultralytics.com/license) のAGPL-3.0の条件に従い、公開時は対応する本プロジェクト全ソースと設定を公開する。重みはGitに含めずスクリプトで取得しSHA256検証する。モデル出力スコアを正解率と呼ばない。
- 人物はOSに同梱された Gazebo Classic `media/models/walk.dae` を実行時に参照。個人の `~/.gazebo/models` から取得しない。人物メッシュを本リポジトリには再配布しない。[actor公式説明](https://classic.gazebosim.org/tutorials?tut=actor)。
- ROS 2 Humble / Gazebo Classic / OpenCV / PyTorch は既存コンテナのインストールを使用。教材検証の静止画は実際のGazebo RGBセンサー出力。
