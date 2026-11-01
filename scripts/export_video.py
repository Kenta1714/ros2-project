#!/usr/bin/python3
"""Add explanatory cards to actual ROS/Gazebo recording, with no speed change."""
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont
root=Path(__file__).resolve().parent.parent
out=root/'recordings/submission';out.mkdir(parents=True,exist_ok=True)
font='/usr/share/fonts/truetype/takao-gothic/TakaoPGothic.ttf'
def card(name,title,lines):
 im=Image.new('RGB',(1280,720),'#12202e');d=ImageDraw.Draw(im)
 d.text((65,75),title,font=ImageFont.truetype(font,42),fill='#64ddd0')
 for i,line in enumerate(lines):d.text((65,190+70*i),line,font=ImageFont.truetype(font,29),fill='white')
 im.save(out/(name+'.png'))
def run(args):subprocess.run(['ffmpeg','-y','-loglevel','error']+args,check=True)
card('intro','人物を検出したら停止する巡回ロボット',[
 '目的：障害物を避けて走行し、人を見つけたら停止',
 'AI：COCO事前学習済みYOLOv8nをCPUで推論',
 '人物スコア0.5以上を異なる2画像で連続検出 → 停止保持',
 '左：Gazebo全体像　右：搭載カメラと検出枠',
 '実行画面を記録（再生速度変更なし・最新受信画像を表示）'])
card('outro','工夫と確認できた範囲',[
 '工夫：カメラ調整、検出と制御の分離、連続検出と停止保持',
 'LiDARの回避はルール制御。停止判断に人物座標は使わない。',
 '同じ初期配置で2回、巡回 → 人物検出 → 停止を再現',
 '限定した人物モデル・環境での確認。実機安全性は未検証。',
 '教材：AI-Robot-Book-Humble　検出：Ultralytics YOLOv8n'])
for name,seconds in [('intro',10),('outro',10)]:
 run(['-loop','1','-i',str(out/(name+'.png')),'-t',str(seconds),'-r','10','-c:v','libx264','-preset','ultrafast','-crf','23','-pix_fmt','yuv420p',str(out/(name+'.mp4'))])
(out/'caption.txt').write_text('左：Gazebo全体像　　右：搭載カメラ / YOLOv8n\n巡回 → 障害物回避 → 人物を連続検出 → 停止保持')
(out/'footer.txt').write_text('CPU推論 / 追加学習なし / 速度指令と実速度は別途ログで確認\nソフトウェア描画：シミュレーションの進行は実時間より遅い')
vf=f"pad=1280:720:0:100:black,drawtext=fontfile={font}:textfile={out}/caption.txt:fontsize=26:fontcolor=white:x=25:y=14:line_spacing=8,drawtext=fontfile={font}:textfile={out}/footer.txt:fontsize=22:fontcolor=white:x=25:y=638:line_spacing=8"
run(['-i',str(root/'recordings/final2/camera.mp4'),'-vf',vf,'-r','10','-c:v','libx264','-preset','ultrafast','-crf','23','-pix_fmt','yuv420p',str(out/'demo.mp4')])
(out/'concat.txt').write_text(''.join(f"file '{name}.mp4'\n" for name in ['intro','demo','outro']))
run(['-f','concat','-safe','0','-i',str(out/'concat.txt'),'-c','copy','-movflags','+faststart',str(root/'recordings/submission.mp4')])
