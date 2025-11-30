"""
protocol.py
自定义通信协议定义
"""

import json

# ---- 消息类型常量 ----
MSG_DRAW = "draw"              # 绘图数据
MSG_GUESS = "guess"            # 猜词请求
MSG_CHAT = "chat"              # 普通聊天
MSG_WELCOME = "welcome"        # 登录成功后服务器返回的信息
MSG_PLAYER_JOIN = "player_join"
MSG_PLAYER_LEAVE = "player_leave"
MSG_ROUND_START = "round_start"  # 回合开始（广播提示）
MSG_ASSIGN_WORD = "assign_word"  # 私发给画手（具体答案）
MSG_ROUND_RESULT = "round_result" # 回合结束（广播结果）
MSG_SYSTEM = "system"          # 系统消息
MSG_SET_NAME = "set_name"      # 客户端发送昵称
MSG_READY = "ready"            # 客户端发送准备状态
MSG_UPDATE_PLAYERS = "update_players"       # 专门用于同步玩家列表（分数、准备状态）

# ---- JSON 编 / 解码工具 ----
def encode_message(obj):
    """
    将 Python 字典编码为字节流，末尾补换行符
    """
    text = json.dumps(obj, ensure_ascii=False)
    return (text + "\n").encode("utf-8")

def decode_stream(buffer):
    """
    将 TCP 缓冲区内容按行切割成完整 JSON 消息
    返回：(messages_list, remaining_buffer)
    """
    lines = buffer.split("\n")
    msgs = []

    # 处理完整的行
    for line in lines[:-1]:
        line = line.strip()
        if not line:
            continue
        try:
            msgs.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    # 剩下的最后一部分（可能不完整）留到下一次
    remaining = lines[-1]
    return msgs, remaining