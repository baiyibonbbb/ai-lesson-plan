from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from docx import Document
import openai
import io
import base64
import os
import re
import functools
import logging
import time

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.static_folder = '.'
app.static_url_path = ''

openai.api_key = os.getenv("ARK_API_KEY")
openai.api_base = "https://ark.cn-beijing.volces.com/api/v3"
MODEL_ID = os.getenv("ARK_MODEL_ID")

TEMPLATE_PATH = "模板.docx"
PROMPT_FILE = "AI 生成教案专用指令.txt"

# 启动时预加载模板和指令
logger.info("正在预加载模板和指令...")
doc_template = Document(TEMPLATE_PATH)
with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    AI_PROMPT = f.read()

# 带重试机制的AI生成
@functools.lru_cache(maxsize=100)
def generate_content(topic):
    full_prompt = AI_PROMPT + "\n课程主题：" + topic
    logger.info(f"开始生成：{topic}")
    start_time = time.time()
    for attempt in range(3):  # 最多重试3次
        try:
            response = openai.ChatCompletion.create(
                model=MODEL_ID,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=0.1,
                max_tokens=2000,
                request_timeout=120  # 单次请求超时2分钟
            )
            content = response.choices[0].message.content
            logger.info(f"生成完成，耗时：{time.time()-start_time:.2f}秒")
            return content
        except Exception as e:
            logger.warning(f"生成失败，重试 {attempt+1}/3：{e}")
            time.sleep(5)
    raise Exception("AI生成多次失败")

def parse_ai_output(text):
    data = {}
    matches = re.findall(r"&(\d+)&(.*?)&\1&", text)
    for idx, content in matches:
        data[f"&{idx}&"] = content
    return data

def fill_template(content_map):
    doc = Document(TEMPLATE_PATH)
    for para in doc.paragraphs:
        for k, v in content_map.items():
            if k in para.text:
                para.text = para.text.replace(k, v)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for k, v in content_map.items():
                        if k in para.text:
                            para.text = para.text.replace(k, v)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

@app.route('/')
def index():
    return send_from_directory('.', 'web.html')

@app.route('/coze/plugin', methods=['GET', 'POST'])
def plugin():
    topic = request.args.get('topic') or (request.json.get('topic') if request.json else None)
    if not topic:
        return jsonify({"status": "error", "message": "need topic"}), 400
    try:
        ai_text = generate_content(topic)
        content = parse_ai_output(ai_text)
        buffer = fill_template(content)
        b64 = base64.b64encode(buffer.read()).decode()
        return jsonify({
            "status": "success",
            "filename": f"{topic}_教案.docx",
            "file_base64": b64
        })
    except Exception as e:
        logger.error(f"处理失败：{e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health')
def health():
    return "ok", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)