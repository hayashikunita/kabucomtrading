"""
Streamlit app.pyのuse_container_widthをwidthパラメータに変換
"""

# ファイル読み込み
with open('streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 置換
content = content.replace('use_container_width=True', "width='stretch'")
content = content.replace('use_container_width=False', "width='content'")

# ファイル書き込み
with open('streamlit_app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 置換完了: use_container_width -> width")
