# config.py

import chainlit as cl
import yaml


def load_config(config_path="config.yml"):
    """
    讀取 YAML 格式的配置文件。

    Args:
        config_path (str): 配置文件的路徑。

    Returns:
        dict: 配置內容，如果讀取失敗則返回 None。
    """
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
            return config
    except FileNotFoundError:
        cl.logger.error(f"配置文件 {config_path} 不存在")
        return None
    except yaml.YAMLError as e:
        cl.logger.error(f"配置文件解析失敗: {str(e)}")
        return None


# 載入配置
config = load_config()

# 如果配置未成功載入，停止應用程式
if config is None:
    cl.stop("配置文件讀取失敗")
