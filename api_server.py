from flask import Flask, request, jsonify
from flask_cors import CORS
from docx import Document
import openai
import json
import io
import base64
import os

app = Flask(__name__)
CORS(app)

# 火山方舟API配置（和你本地的保持一致）
openai.api_key = os.getenv("ARK_API_KEY")
openai.api_base = "https://ark.cn-beijing.volces.com/api/v3"
MODEL_ID = os.getenv("ARK_MODEL_ID")

# 模板文件路径（和你的文件同名，必须放在项目根目录）
TEMPLATE_PATH = "模板.docx"

def generate_lesson_content(topic):
    """生成教案内容，强制按JSON格式输出"""
    prompt = f"""
    请为《{topic}》课程生成一份标准教案，严格按照以下JSON格式输出，不要添加任何其他内容：
    {{
        "course_name": "课程名称",
        "content_analysis": "内容分析",
        "quality_goal": "素质目标",
        "knowledge_goal": "知识目标",
        "ability_goal": "能力目标",
        "key_points": "教学重点",
        "difficult_points": "教学难点"
    }}
    """
    response = openai.ChatCompletion.create(
        model=MODEL_ID,
        messages=[{"role": "user", "content": prompt}]
    )
    return json.loads(response.choices[0].message.content)

def fill_template(content):
    """填充模板，遍历所有段落和表格，解决占位符不替换问题"""
    doc = Document(TEMPLATE_PATH)
    
    # 占位符映射，和你模板里的&1&到&7&完全对应
    placeholders = {
        "&1&": content["course_name"],
        "&2&": content["content_analysis"],
        "&3&": content["quality_goal"],
        "&4&": content["knowledge_goal"],
        "&5&": content["ability_goal"],
        "&6&": content["key_points"],
        "&7&": content["difficult_points"]
    }

    # 1. 替换普通段落中的占位符
    for paragraph in doc.paragraphs:
        for key, value in placeholders.items():
            if key in paragraph.text:
                paragraph.text = paragraph.text.replace(key, value)

    # 2. 替换表格单元格中的占位符（解决你之前表格里的占位符不替换问题）
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for key, value in placeholders.items():
                        if key in paragraph.text:
                            paragraph.text = paragraph.text.replace(key, value)

    # 3. 直接在内存中保存为文件流，不写入磁盘
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

@app.route('/coze/plugin', methods=['GET'])
def coze_plugin():
    topic = request.args.get('topic')
    if not topic:
        return jsonify({"status": "error", "message": "缺少topic参数"}), 400

    try:
        # 步骤1：生成教案内容
        content = generate_lesson_content(topic)
        # 步骤2：填充模板，生成文件流
        buffer = fill_template(content)
        # 步骤3：转成base64，一次性传给Coze，不会有文件丢失问题
        file_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        return jsonify({
            "status": "success",
            "filename": f"{topic}_教案.docx",
            "file_base64": file_base64
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)