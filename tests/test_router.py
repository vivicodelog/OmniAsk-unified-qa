"""
测试router。
"""

from fastapi.testclient import TestClient
from backend import file_router
from backend.main import app

client = TestClient(app)  # 把 app 包一层，发请求不走网络

# ===== 测上传 =====
def test_upload_xlsx():
    # 1. 用二进制模式打开文件
    with open("data/sample_sales.xlsx", "rb") as f:
        # 2. files 参数就是 HTML form-data
        response = client.post("/api/upload", files={"file": ("sales.xlsx", f)})

    # 3. 跟 curl 返回一样，response.json() 拿响应体
    assert response.status_code == 200
    body = response.json()
    assert body["file_type"] == "xlsx"
    assert "session_id" in body
def test_upload_csv():
    # 1. 用二进制模式打开文件
    with open("data/sample_sales.csv", "rb") as f:
        # 2. files 参数就是 HTML form-data
        response = client.post("/api/upload", files={"file": ("sales.csv", f)})

    # 3. 跟 curl 返回一样，response.json() 拿响应体
    assert response.status_code == 200
    body = response.json()
    assert body["file_type"] == "csv"
    assert "session_id" in body

def test_no_file():
    response = client.post("/api/upload")
    assert response.status_code == 422

# ===== 测 chat 不存在 =====
def test_chat_session_not_found():
    response = client.post("/api/chat", json={
        "session_id": "不存在的ID",
        "question": "随便问",
    })
    assert response.status_code == 200
    assert response.json()["error"] == "会话不存在"
def test_chat():
    session_id, ctx = file_router._new_session()
    ctx.agent.run = lambda question, schema, db, guard: {
        "sql": "SELECT 产品, SUM(销量) FROM qa_test_0 GROUP BY 产品",
        "data": [{"产品": "A", "销量": 100}, {"产品": "B", "销量": 200}],
        "success": True,
    }

    response = client.post("/api/chat", json={
        "session_id": session_id,
        "question": "各产品销量占比是多少",
    })
    assert response.json()["sql"] == "SELECT 产品, SUM(销量) FROM qa_test_0 GROUP BY 产品"
    assert response.json()["chart_type"] == "pie"
