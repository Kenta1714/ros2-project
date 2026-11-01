#!/usr/bin/python3
"""Export the Japanese Markdown report with the image's existing ReportLab."""
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
from reportlab.lib.pagesizes import A4
root=Path(__file__).resolve().parent.parent
pdfmetrics.registerFont(TTFont('Japanese','/usr/share/fonts/truetype/takao-gothic/TakaoPGothic.ttf'))
body=ParagraphStyle('body',fontName='Japanese',fontSize=9,leading=14,wordWrap='CJK',spaceAfter=5)
heading=ParagraphStyle('heading',parent=body,fontSize=11,leading=16,spaceBefore=7)
title=ParagraphStyle('title',parent=body,fontSize=16,leading=22,spaceAfter=12)
story=[]
for block in (root/'docs/report.md').read_text().split('\n\n'):
 style=title if block.startswith('# ') else heading if block.startswith('## ') else body
 story.append(Paragraph(escape(block.lstrip('# ').strip()).replace('\n','<br/>'),style))
SimpleDocTemplate(str(root/'docs/report.pdf'),pagesize=A4,rightMargin=40,leftMargin=40,topMargin=35,bottomMargin=35,title='人物を検出したら停止する巡回ロボット',author='').build(story)
