@echo off
echo Converting Word document to text format...
cd /d "C:\Users\qiaoshuowen\clawd\skills\AI-Plat"
python utils\document_processor.py "C:\Users\qiaoshuowen\Downloads\融合版_V3.2_概要设计.docx" "C:\Users\qiaoshuowen\clawd\skills\AI-Plat\fusion_design_spec.txt"
echo Conversion complete! Check the fusion_design_spec.txt file.
pause