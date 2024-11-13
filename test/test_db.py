# test_db_connection.py

import yaml
from sqlalchemy import create_engine


def test_connection():
    # 载入配置文件
    with open("../config.yml", "r") as file:
        config = yaml.safe_load(file)

    postgres_connection_string = config.get("postgres_connection_string")

    try:
        engine = create_engine(postgres_connection_string)
        connection = engine.connect()
        print("資料庫連接成功！")
        connection.close()
    except Exception as e:
        print("資料庫連接失敗：", e)


if __name__ == "__main__":
    test_connection()
