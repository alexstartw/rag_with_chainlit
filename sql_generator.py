# sql_generator.py

from config import config
from langchain_community.llms.openai import OpenAI
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from openai import OpenAIError

import prompt

# Get configuration parameters
postgres_connection_string = config.get("postgres_connection_string")
openai_api_key = config.get("openai_api_key")
model_name = config.get("model_name")

# Ensure configuration parameters exist
if not postgres_connection_string:
    raise ValueError("config.yml 中缺少 'postgres_connection_string'")
if not openai_api_key:
    raise ValueError("config.yml 中缺少 'openai_api_key'")

# Set OpenAI API key

# Connect to the database and capture potential errors
try:
    db = SQLDatabase.from_uri(
        postgres_connection_string,
        include_tables=[
            "employees_demo",
            "employeeattendance_demo",
            "employeeleave_demo",
        ],
    )
    print("資料庫連接成功並加載指定表格。")
except Exception as e:
    print("資料庫連接失敗：", e)
    raise e


_DEFAULT_TEMPLATE = prompt.sql_prompt


def sql_assistant(prompt):
    try:
        # Create LLMChain
        llm = OpenAI(temperature=0, openai_api_key=openai_api_key)

        # Create SQLDatabaseChain using custom prompt
        db_chain = SQLDatabaseChain(
            llm=llm,
            database=db,
            verbose=True,
            use_query_checker=True,
            return_intermediate_steps=True,
            top_k=100,
        )

        input_query = _DEFAULT_TEMPLATE.format(question=prompt)
        print("input_query:", input_query)

        # Execute the chain
        result = db_chain.invoke(input_query)

        # Extract generated SQL command from intermediate_steps
        intermediate_steps = result.get("intermediate_steps", [])
        sql_command = None
        if intermediate_steps:
            for step in intermediate_steps:
                if "sql_cmd" in step:
                    sql_command = step.get("sql_cmd", "").rstrip(";").strip()
                    break

        if not sql_command:
            return {"error": "未能生成 SQL 查詢指令。"}

        # Final result is in 'result'
        sql_result = result.get("result", "")
        print("sql_result", sql_result)

        if not sql_result:
            return {"sql_command": sql_command, "sql_result": "本次查詢無結果。"}

        return {"sql_command": sql_command, "sql_result": sql_result}

    except OpenAIError as e:
        print("在執行 SQLDatabaseChain 時出錯：", e)
        return {"error": f"OpenAI 錯誤: {str(e)}"}

    except Exception as e:
        print("發生錯誤：", e)
        return {"error": f"未知錯誤: {str(e)}"}


# Define the sql_question function for external use
def sql_question(question):
    result = sql_assistant(question)
    if result:
        if "error" in result:
            return result["error"]
        return result.get("sql_result", "無結果")
    return "查詢失敗，請稍後再試。"
