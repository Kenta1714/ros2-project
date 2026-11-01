# ロボット資産のコピー元と変更点

コピー元：AI-Robot-Book-Humble/turtlebot3_happy_mini の `turtlebot3_simulations/turtlebot3_gazebo/models/turtlebot3_happy_mini`（このコンテナに同梱された版）。

- `model.sdf`、メッシュ、テクスチャ等は教材からコピーしたもの。
- `model_camera_fixed.sdf` は検証用の派生版で、camera_linkとcamera_rgb_optical_frameのposeを明示した。XMLシリアライズによる書式変更・コメント省略もある。
- 実行時にstatic指定、他センサー停止、モータープラグイン停止、カメラのnamespace・更新レートを変更する。元の教材ファイルは変更していない。
- `turtlebot3_happy_mini_LICENSE`、`turtlebot3_happy_mini_NOTICE`、`turtlebot3_simulations_LICENSE` はコピー元の表記を保持したもの。
- 人物walk.daeはこのディレクトリに複製せず、Gazebo標準インストールを参照する。

元モデルと元資産のSHA256は `source_assets.sha256` に記録する。

本実装時にメッシュ・テクスチャを `src/vendor/turtlebot3_gazebo/models/turtlebot3_happy_mini/` へ統合した。ここには比較用SDFだけを残し、validate.pyがvendor側のメッシュを参照する。source_assets.sha256はコピー時点の記録であり、移動後の相対パスではない。
