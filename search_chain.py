import chainlit as cl
import logging
import json
from config import config
from rag_search import rag_question, template_type
from sql_generator import sql_question
import prompt

# 初始化 OpenAI LLM
openai_api_key = config.get("openai_api_key")
model_name = config.get("model_name")


# 定義自定義 ChatOpenAI Prompt
def custom_openai_prompt(question):
    system_template = prompt.outer_prompt
    user_template = (
        f"問題: {question}。請以 JSON 格式提供分類結果，輸出應包括 'Category', 'whether need RAG search', 'whether need SQL search' 三個欄位。"
    )
    # 返回格式化的提示
    return f"{system_template}\n{user_template}"

# 定義 ChatOpenAI 模型與 prompt 結合
def get_openai_response(question):
    prompt_text = custom_openai_prompt(question)

    # 延遲導入 ChatOpenAI 來避免循環導入
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=model_name, openai_api_key=openai_api_key, temperature=0.7, streaming=True
    )

    # 使用 invoke 來進行查詢，返回的是 AIMessage 對象
    response = llm.invoke(prompt_text)

    # 返回 AIMessage 的 content
    return response.content


# 定義 RAG Chain
async def rag_chain(question):
    # 先用 OpenAI 進行背景知識補充
    additional_context = get_openai_response(question)

    # 將額外的上下文加入 RAG 查詢
    rag_result = rag_question(f"{question} 背景信息: {additional_context}")
    return rag_result


# 定義 SQL Chain
async def sql_chain(question):
    # 基於查詢的結果生成 SQL 查詢
    sql_query = sql_question(question)
    return sql_query


# 使用 SequentialChain 串接 RAG 和 SQL Chain
async def sequential_chain(question):
    # Step 1: 進行 OpenAI 查詢以獲取分類結果
    classification_response = get_openai_response(question)
    logging.info(f"分類結果: {classification_response}")

    classification_response = classification_response.replace("```json", "").replace("```", "").strip()

    # 解析分類結果，確認應該使用哪個分類
    try:
        # 提取 `content` 並解析為 JSON
        classification_data = json.loads(classification_response)
        category = classification_data.get("Category")
        need_rag_search = classification_data.get("whether need RAG search")
        need_sql_search = classification_data.get("whether need SQL search")
    except Exception as e:
        logging.error(f"分類結果解析失敗: {str(e)}")
        return "分類失敗，請稍後再試"

    # Step 2: 根據分類結果進行查詢操作
    if need_rag_search == "Yes":
        # 進行 RAG 查詢並傳遞 category
        logging.info(f"進行 RAG 查詢，分類為: {category}")
        template_type(category)
        rag_result = await rag_chain(question)
        logging.info(f"RAG 查詢結果: {rag_result}")

        # 如果 RAG 結果有效，直接返回
        if rag_result:
            return  rag_result

    if need_sql_search == "Yes":
        # 如果 RAG 查詢無效或不需要，進行 SQL 查詢並傳遞 category
        logging.info(f"進行 SQL 查詢，分類為: {category}")
        sql_query = await sql_chain(question)
        logging.info(f"生成的 SQL 查詢: {sql_query}")

        # 檢查 SQL 查詢結果是否是「本次查詢無結果」
        if "本次查詢無結果" in sql_query:
            return f"查詢不到結果"

        # 返回 SQL 查詢結果
        return sql_query if sql_query else "查詢不到結果"

    return f"這個問題不需要 RAG 或 SQL 查詢"

# 定義 Chainlit 回調函數

# 這個回調函數在聊天啟動時調用
@cl.on_chat_start
async def handle_chat_start():
    print("Chat started")  # 這裡可以進行初始化工作
    await cl.Message(content="歡迎來到 HR 查詢系統！請問有什麼我可以幫忙的？").send()


# 這個回調函數在每次收到消息時調用
@cl.on_message
async def handle_message(message: cl.Message):
    print("Message received")
    user_question = message.content.strip()  # 提取並去除用戶輸入的多餘空格

    if user_question:  # 確保有輸入內容
        try:
            # 傳遞問題給 sequential_chain 進行 RAG 和 SQL 查詢
            query_result = await sequential_chain(user_question)+ "\n\n以上資訊僅供參考，詳細資訊請查閱相關規章 !"
            # 發送查詢結果給用戶
            await cl.Message(content=query_result).send()

        except Exception as e:
            # 記錄錯誤日誌並告知用戶查詢失敗
            logging.error(f"查詢過程中出現錯誤: {str(e)}")
            await cl.Message(content="查詢失敗，請稍後再試").send()
    else:
        # 如果用戶沒有輸入任何內容
        await cl.Message(content="請輸入問題！").send()
