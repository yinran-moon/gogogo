# GoGoGo - Streamlit 部署版

这是 `GoGoGo` 项目的单体化 Streamlit 版本，专为在 [Streamlit Community Cloud](https://streamlit.io/cloud) 等 Serverless 平台上快速部署和演示而设计。

它将原本分离的 FastAPI 后端和 Next.js 前端合并为了一个纯 Python 的交互式 Web 应用，保留了 LangGraph 核心编排、RAG 检索和多模型路由的全部能力。

## 部署到 Streamlit Cloud 的步骤

1. **上传到 GitHub**
   将本文件夹（`streamlit_deploy`）下的所有内容作为一个新的 GitHub 仓库（或放在仓库根目录）。

2. **连接 Streamlit Cloud**
   - 登录 [share.streamlit.io](https://share.streamlit.io/)
   - 点击 `New app` -> 选择你的 GitHub 仓库
   - `Main file path` 填写 `app.py`

3. **配置 Secrets (环境变量)**
   在部署页面的 `Advanced settings` -> `Secrets` 中填入你的 API Key：
   ```toml
   QWEN_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
   ```
   *(如果不配置，用户也可以在网页侧边栏手动输入)*

4. **点击 Deploy**
   等待几分钟安装依赖，即可在线访问！

## 目录说明

- `app.py`: Streamlit 前端交互页面和主入口
- `app/`: 核心业务逻辑（Agent 编排、LiteLLM 路由、RAG 服务等）
- `data/`: 本地知识库和 ChromaDB 向量索引（已随代码提交，开箱即用）
- `requirements.txt`: Python 依赖清单（包含 `pysqlite3-binary` 解决云端 SQLite 版本过低问题）

## 本地运行测试

如果你想在本地测试这个 Streamlit 版本：

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行应用
streamlit run app.py
```
