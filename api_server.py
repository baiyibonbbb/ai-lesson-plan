from flask import Flask, request, jsonify, send_from_directory # 新增 send_from_directory
from flask_cors import CORS
from docx import Document
import openai
import json
import io
import base64
import os

app = Flask(__name__)
CORS(app)

# 新增：设置静态文件目录为当前目录
app.static_folder = '.'
app.static_url_path = ''

# ...（中间你的原有代码）...

# ===================== 新增web.html路由 =====================
@app.route('/')
def index():
    return send_from_directory('.', 'web.html')
# ==========================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)