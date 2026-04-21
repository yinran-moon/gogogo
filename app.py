import sys
# 解决 Streamlit Cloud 上 SQLite 版本过低的问题 (ChromaDB 需要 sqlite3 >= 3.35.0)
__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import streamlit as st
import asyncio
import json
import re
import os

from app.agents.orchestrator import agent_graph, AgentState
from app.core.config import get_settings

# --- 页面配置 ---
st.set_page_config(
    page_title="GoGoGo - AI旅行规划陪跑助手",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 环境变量/Secrets 注入 ---
# 允许用户在侧边栏输入 API Key，或者从 Streamlit Secrets 读取
settings = get_settings()
if "QWEN_API_KEY" in st.secrets:
    os.environ["QWEN_API_KEY"] = st.secrets["QWEN_API_KEY"]

# --- 会话状态初始化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent_state" not in st.session_state:
    st.session_state.agent_state = AgentState(
        phase="profile_collecting",
        messages=[],
        profile={},
        destination="",
        days=3,
        itinerary={},
        last_response="",
        user_input="",
    )

# --- 辅助函数 ---
def run_async(coro):
    """运行异步函数的辅助方法"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        # 如果已经在事件循环中，使用 nest_asyncio 或创建新线程（Streamlit 通常不在异步循环中）
        import nest_asyncio
        nest_asyncio.apply()
        return asyncio.run(coro)
    return asyncio.run(coro)

def parse_json_blocks(text: str):
    """简单解析 Markdown 中的 JSON 块并渲染"""
    parts = re.split(r'```json\s*([\s\S]*?)```', text)
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip():
                st.markdown(part)
        else:
            try:
                data = json.loads(part)
                st.json(data)
            except json.JSONDecodeError:
                st.code(part, language="json")

# --- 侧边栏 ---
with st.sidebar:
    st.title("🧭 GoGoGo")
    st.caption("AI 驱动的全链路旅行规划与陪跑助手")
    
    st.divider()
    
    # API Key 配置
    api_key = st.text_input("通义千问 API Key (Qwen)", type="password", 
                            value=os.environ.get("QWEN_API_KEY", ""),
                            help="如果没有在 Secrets 中配置，请在此输入")
    if api_key:
        os.environ["QWEN_API_KEY"] = api_key
        
    st.divider()
    
    # 状态展示
    st.subheader("📊 当前状态")
    phase_map = {
        "profile_collecting": "📝 了解你",
        "inspiration": "💡 灵感种草",
        "planning": "📅 行程规划",
        "companion": "🚶 出行陪跑",
        "review": "📖 旅后复盘"
    }
    current_phase = st.session_state.agent_state.get("phase", "profile_collecting")
    st.info(f"**当前阶段**：{phase_map.get(current_phase, current_phase)}")
    
    if st.session_state.agent_state.get("destination"):
        st.success(f"**目的地**：{st.session_state.agent_state['destination']}")
        
    with st.expander("👤 用户画像", expanded=False):
        st.json(st.session_state.agent_state.get("profile", {}))
        
    with st.expander("🗺️ 行程单", expanded=False):
        st.json(st.session_state.agent_state.get("itinerary", {}))
        
    if st.button("🔄 重新开始", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent_state = AgentState(
            phase="profile_collecting", messages=[], profile={}, destination="", days=3, itinerary={}, last_response="", user_input=""
        )
        st.rerun()

# --- 主界面 ---
st.header("✈️ 开启你的专属旅行")

# 渲染历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🧭"):
        if msg["role"] == "assistant":
            parse_json_blocks(msg["content"])
        else:
            st.markdown(msg["content"])

# 聊天输入
if prompt := st.chat_input("告诉我你的旅行想法吧，比如想去哪、几个人、预算多少..."):
    if not os.environ.get("QWEN_API_KEY"):
        st.error("请先在左侧边栏输入通义千问 API Key！")
        st.stop()
        
    # 显示用户输入
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)
        
    # 调用 Agent
    with st.chat_message("assistant", avatar="🧭"):
        with st.spinner("思考中..."):
            # 更新状态
            state = st.session_state.agent_state
            state["user_input"] = prompt
            
            try:
                # 执行图
                new_state = run_async(agent_graph.ainvoke(state))
                st.session_state.agent_state = new_state
                
                response = new_state["last_response"]
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                # 渲染回复
                parse_json_blocks(response)
                
            except Exception as e:
                st.error(f"发生错误: {str(e)}")
