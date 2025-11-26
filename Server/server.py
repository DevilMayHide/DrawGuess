import socket
import threading
import sys
import random
import time
from pathlib import Path

# 添加项目根目录到路径，以便导入 Shared
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from Shared.protocol import *

class GameState:
    """维护游戏全局状态：玩家、分数、回合信息"""
    def __init__(self):
        self.lock = threading.Lock()
        
        self.clients = {}       # socket -> player_name
        self.name_to_conn = {}  # player_name -> socket
        
        self.scores = {}        # player_name -> int
        self.ready_players = set() # set(player_name)
        
        self.game_in_progress = False
        self.current_drawer = None
        self.current_answer = None
        self.round_id = 0
        
        # 加载词库
        self.words = self._load_words()

    def _load_words(self):
        path = ROOT_DIR / "words.txt"
        default_words = ["苹果", "香蕉", "电脑", "太阳", "月亮", "汽车", "房子"]
        if not path.exists():
            return default_words
        try:
            content = path.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            return lines if lines else default_words
        except Exception:
            return default_words

    def add_player(self, conn, name):
        with self.lock:
            # 处理重名
            original_name = name
            count = 2
            while name in self.name_to_conn:
                name = f"{original_name}({count})"
                count += 1
            
            self.clients[conn] = name
            self.name_to_conn[name] = conn
            if name not in self.scores:
                self.scores[name] = 0
            return name

    def remove_player(self, conn):
        with self.lock:
            name = self.clients.pop(conn, None)
            if name:
                self.name_to_conn.pop(name, None)
                self.ready_players.discard(name)
                # 如果当前画手掉了，结束回合的逻辑比较复杂，这里简化为重置游戏状态
                if self.game_in_progress and name == self.current_drawer:
                    self.game_in_progress = False
                    self.current_drawer = None
            return name

    def set_ready(self, name):
        with self.lock:
            self.ready_players.add(name)
            # 检查是否所有人都准备好了
            total_players = len(self.clients)
            if total_players >= 2 and len(self.ready_players) == total_players:
                return True
            return False

    def reset_round_state(self):
        """回合结束或开始前重置准备状态"""
        with self.lock:
            self.ready_players.clear()
            self.game_in_progress = False
            self.current_drawer = None
            self.current_answer = None

class GuessDrawServer:
    def __init__(self, host="0.0.0.0", port=9000):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.game = GameState()
        self.running = False

    def start(self):
        try:
            self.sock.bind((self.host, self.port))
            self.sock.listen(5)
            # 设置超时，让 accept 循环能响应停止信号
            self.sock.settimeout(1.0)
            self.running = True
            print(f"[SERVER] 启动成功 {self.host}:{self.port}")
            print("[SERVER] 等待连接...")

            while self.running:
                try:
                    conn, addr = self.sock.accept()
                    print(f"[SERVER] 新连接: {addr}")
                    t = threading.Thread(target=self.handle_client, args=(conn,), daemon=True)
                    t.start()
                except socket.timeout:
                    continue
                except OSError:
                    break
        except Exception as e:
            print(f"[SERVER] 启动错误: {e}")
        finally:
            self.stop()

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except:
            pass
        print("[SERVER] 服务器已停止")

    def broadcast(self, msg, exclude=None):
        data = encode_message(msg)
        # 这里为了防止遍历字典时修改，使用 list(keys)
        with self.game.lock:
            conns = list(self.game.clients.keys())

        for conn in conns:
            if conn == exclude:
                continue
            try:
                conn.sendall(data)
            except OSError:
                pass # 发送失败由 handle_client 中的 recv 异常处理

    def send_to(self, conn, msg):
        try:
            conn.sendall(encode_message(msg))
        except OSError:
            pass

    def start_new_round(self):
        """开始新的一轮：选人、选题、广播"""
        with self.game.lock:
            players = list(self.game.name_to_conn.keys())
            if not players:
                return
            
            self.game.round_id += 1
            self.game.current_drawer = random.choice(players)
            self.game.current_answer = random.choice(self.game.words)
            self.game.game_in_progress = True
            # 清空准备状态，等待下一轮
            self.game.ready_players.clear()

            drawer = self.game.current_drawer
            answer = self.game.current_answer
            round_id = self.game.round_id
            
            drawer_conn = self.game.name_to_conn.get(drawer)

        print(f"[GAME] Round {round_id}: Drawer={drawer}, Answer={answer}")

        # 1. 广播回合开始（只包含提示）
        self.broadcast({
            "type": MSG_ROUND_START,
            "round": round_id,
            "drawer": drawer,
            "hint": f"{len(answer)} 个字"
        })

        # 2. 私聊告诉画手题目
        if drawer_conn:
            self.send_to(drawer_conn, {
                "type": MSG_ASSIGN_WORD,
                "word": answer
            })

    def handle_client(self, conn):
        player_name = None
        buffer = ""

        try:
            # 1. 握手阶段：等待 MSG_SET_NAME
            while True:
                data = conn.recv(1024)
                if not data:
                    return
                buffer += data.decode("utf-8")
                msgs, buffer = decode_stream(buffer)
                
                # 寻找 set_name 消息
                for msg in msgs:
                    if msg.get("type") == MSG_SET_NAME:
                        raw_name = msg.get("name", "Player")
                        if not raw_name.strip(): 
                            raw_name = "Player"
                        player_name = self.game.add_player(conn, raw_name)
                        break
                if player_name:
                    break
            
            # 2. 发送欢迎信息 & 广播加入
            print(f"[SERVER] {player_name} 加入游戏")
            with self.game.lock:
                # 构建玩家列表数据： [{"name": "P1", "score": 0, "is_ready": False}, ...]
                p_list = []
                for p_name, p_score in self.game.scores.items():
                    p_list.append({
                        "name": p_name,
                        "score": p_score,
                        "is_ready": p_name in self.game.ready_players
                    })

            self.send_to(conn, {
                "type": MSG_WELCOME,
                "player_name": player_name,
                "players": p_list,
                "round": self.game.round_id,
                "in_game": self.game.game_in_progress,
                "drawer": self.game.current_drawer
            })
            
            self.broadcast({
                "type": MSG_PLAYER_JOIN,
                "player_name": player_name
            }, exclude=conn)

            # 3. 游戏循环
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8")
                msgs, buffer = decode_stream(buffer)

                for msg in msgs:
                    self._process_message(conn, player_name, msg)

        except (ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            print(f"[ERROR] {player_name}: {e}")
        finally:
            if player_name:
                print(f"[SERVER] {player_name} 断开连接")
                self.game.remove_player(conn)
                self.broadcast({
                    "type": MSG_PLAYER_LEAVE,
                    "player_name": player_name
                })
            conn.close()

    def _process_message(self, conn, player_name, msg):
        mtype = msg.get("type")

        if mtype == MSG_READY:
            # 只有不在游戏中才能准备
            if not self.game.game_in_progress:
                all_ready = self.game.set_ready(player_name)
                # 广播状态变更
                self.broadcast({
                    "type": MSG_SYSTEM, 
                    "text": f"玩家 {player_name} 已准备"
                })
                # 还可以广播一个刷新列表的消息，为了简化，客户端根据 system 消息刷新或单独发 msg 均可
                # 这里我们选择发一个 system 消息，客户端 UI 手动置灰准备按钮即可
                
                if all_ready:
                    self.start_new_round()

        elif mtype == MSG_CHAT:
            # 普通聊天
            text = msg.get("text", "")
            if text:
                self.broadcast({
                    "type": MSG_CHAT,
                    "from": player_name,
                    "text": text
                })

        elif mtype == MSG_GUESS:
            # 猜词
            guess_word = msg.get("text", "").strip()
            answer = self.game.current_answer
            
            # 如果不在游戏中，或者画手自己猜（防作弊）
            if (not self.game.game_in_progress) or (player_name == self.game.current_drawer):
                # 当作普通聊天转发
                self.broadcast({
                    "type": MSG_CHAT,
                    "from": player_name,
                    "text": guess_word
                })
                return

            print(f"[GUESS] {player_name} guess: {guess_word} (Ans: {answer})")
            
            if answer and guess_word == answer:
                # 猜对了
                with self.game.lock:
                    self.game.scores[player_name] += 1
                    # 也可以给画手加分
                    if self.game.current_drawer in self.game.scores:
                        self.game.scores[self.game.current_drawer] += 1
                    
                    scores_snapshot = self.game.scores.copy()
                
                self.broadcast({
                    "type": MSG_ROUND_RESULT,
                    "winner": player_name,
                    "answer": answer,
                    "scores": scores_snapshot
                })
                
                # 结束当前回合状态，等待再次准备
                self.game.reset_round_state()
            else:
                # 猜错了，告诉所有人他猜错了
                self.broadcast({
                    "type": MSG_SYSTEM,
                    "text": f"{player_name} 猜了：{guess_word} (错误)"
                })

        elif mtype == MSG_DRAW:
            # 只有当前画手能画
            if self.game.game_in_progress and player_name == self.game.current_drawer:
                self.broadcast(msg, exclude=conn)

if __name__ == "__main__":
    server = GuessDrawServer()
    # 启动服务器线程
    t = threading.Thread(target=server.start, daemon=True)
    t.start()
    
    print("输入 'q' 退出服务器")
    while True:
        cmd = input()
        if cmd.strip().lower() == 'q':
            server.stop()
            break