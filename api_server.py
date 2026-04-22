from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import re
import os
import requests
from docx import Document
import tempfile

app = FastAPI(title="AI教案生成Coze插件")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== AI 配置 =====================
DOUBAO_API_KEY = "ark-c923f9c20215-4823-bd76-e51cbe57e5fe"
DOUBAO_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
MODEL = "doubao-3-lite"

# ===================== 生成教案 =====================
def generate_lesson_plan(topic: str):
    try:
        with open("AI 生成教案专用指令.txt", "r", encoding="utf-8") as f:
            prompt = f.read().strip()
    except:
        prompt = "你是一名职业院校教师，请生成一份专业、完整、可直接使用的教案。"

    prompt += f"\n课程主题：{topic}"

    headers = {
        "Authorization": f"Bearer {DOUBAO_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        resp = requests.post(DOUBAO_URL, headers=headers, json=data, timeout=120)
        res = resp.json()
        return res["choices"][0]["message"]["content"]
    except Exception as e:
        print("AI错误:", e)
        return ""

# ===================== 解析格式 =====================
def parse_content(text):
    data = {}
    matches = re.findall(r"&(\d+)&(.*?)&", text, re.DOTALL)
    for num, val in matches:
        try:
            data[int(num)] = val.strip()
        except:
            continue
    return data

# ===================== 生成WORD =====================
def create_docx(data):
    doc = Document("模板.docx")
    for p in doc.paragraphs:
        for k, v in data.items():
            p.text = p.text.replace(f"&{k}&", v)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for k, v in data.items():
                        p.text = p.text.replace(f"&{k}&", v)
    tmp = tempfile.mktemp(".docx")
    doc.save(tmp)
    return tmp

# ===================== Coze 插件专用接口 =====================
@app.post("/coze/plugin", summary="Coze插件接口")
def coze_plugin(topic: str):
    if not topic:
        return JSONResponse({"code": 1, "msg": "请输入课程名称"})

    # 生成教案
    content = generate_lesson_plan(topic)
    if not content:
        return JSONResponse({"code": 1, "msg": "AI生成失败"})

    # 解析并生成文档
    data = parse_content(content)
    if not data:
        return JSONResponse({"code": 1, "msg": "教案格式解析失败"})

    docx_path = create_docx(data)

    # 返回 Coze 插件标准格式
    return {
        "code": 0,
        "message": "success",
        "data": {
            "topic": topic,
            "download_url": f"https://ai-lesson-plan-rdxl.onrender.com/generate?topic={topic}",
            "tip": "点击链接直接下载教案 Word 文件"
        }
    }

# ===================== 下载接口 =====================
@app.get("/generate")
def generate(topic: str):
    content = generate_lesson_plan(topic)
    data = parse_content(content)
    docx_file = create_docx(data)
    return FileResponse(docx_file, filename=f"{topic}教案.docx")

# ===================== 网页 =====================
@app.get("/")
def index():
    with open("web.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)