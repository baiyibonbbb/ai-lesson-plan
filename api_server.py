from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import io
import base64
from docx import Document
import openai
import json

app = Flask(__name__)
CORS(app)

# 火山方舟API配置
openai.api_key = os.getenv("ARK_API_KEY")
openai.api_base = "https://ark.cn-beijing.volces.com/api/v3"
MODEL_ID = os.getenv("ARK_MODEL_ID")

# 直接用你本地的模板文件
TEMPLATE_PATH = "模板.docx"

def generate_lesson_content(topic):
    """调用AI生成教案内容"""
    prompt = f"""
    请为《{topic}》课程生成一份标准教案，包含以下内容：
    1. 课程名称
    2. 内容分析
    3. 教学目标（素质目标、知识目标、能力目标）
    4. 教学重点
    5. 教学难点
    请以JSON格式输出，key为：
    "course_name", "content_analysis", "quality_goal", "knowledge_goal", "ability_goal", "key_points", "difficult_points"
    """
    
    response = openai.ChatCompletion.create(
        model=MODEL_ID,
        messages=[{"role": "user", "content": prompt}]
    )
    return json.loads(response.choices[0].message.content)

def fill_template(content, template_path):
    """完整填充Word模板，修复表格占位符问题"""
    doc = Document(template_path)
    
    # 严格匹配你模板里的&1&到&7&占位符
    placeholders = {
        "&1&": content["course_name"],
        "&2&": content["content_analysis"],
        "&3&": content["quality_goal"],
        "&4&": content["knowledge_goal"],
        "&5&": content["ability_goal"],
        "&6&": content["key_points"],
        "&7&": content["difficult_points"]
    }
    
    # 遍历所有段落替换
    for paragraph in doc.paragraphs:
        for key, value in placeholders.items():
            if key in paragraph.text:
                paragraph.text = paragraph.text.replace(key, value)
    
    # 遍历所有表格单元格替换（关键修复！）
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for key, value in placeholders.items():
                        if key in paragraph.text:
                            paragraph.text = paragraph.text.replace(key, value)
    
    # 直接返回内存中的文件流，不存临时文件
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
        # 1. 生成教案内容
        content = generate_lesson_content(topic)
        
        # 2. 填充模板，直接生成内存文件流
        buffer = fill_template(content, TEMPLATE_PATH)
        
        # 3. 转成base64返回，避免403下载问题
        file_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        return jsonify({
            "status": "success",
            "filename": f"{topic}_教案.docx",
            "file_base64": file_base64,
            "message": "教案生成成功，文件内容已直接返回，不会再出现403错误"
        })
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)