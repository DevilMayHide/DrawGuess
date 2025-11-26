import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QListWidget, QLabel,
    QMessageBox, QGroupBox, QInputDialog, QFrame, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QColor, QFont

from draw_widget import DrawWidget
from network import NetworkClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from Shared.protocol import *

# ---- QSS 样式表 ----
STYLESHEET = """
QMainWindow {
    background-color: #f0f2f5;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #dcdcdc;
    border-radius: 5px;
    margin-top: 10px;
    background-color: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QListWidget {
    border: none;
    background-color: #ffffff;
    font-size: 14px;
}
QTextEdit {
    border: none;
    background-color: #ffffff;
    font-size: 13px;
}
QLineEdit {
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 6px;
    font-size: 14px;
}
QPushButton {
    background-color: #0078d4;
    color: white;
    border-radius: 4px;
    padding: 6px 15px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #1084d9;
}
QPushButton:pressed {
    background-color: #006cc1;
}
QPushButton:disabled {
    background-color: #cccccc;
}
/* 特定按钮颜色 */
QPushButton#btn_ready { background-color: #28a745; }
QPushButton#btn_ready:disabled { background-color: #88cc99; }
QPushButton#btn_send { background-color: #17a2b8; }
/* 颜色选择按钮 */
QPushButton#color_btn { border: 2px solid #ddd; border-radius: 10px; }
"""

class MainWindow(QMainWindow):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.player_name = ""
        
        # 游戏状态
        self.is_drawer = False
        self.game_running = False
        self.scores = {} 
        self.ready_status = {}

        self.setWindowTitle("DrawGuess - 你画我猜")
        self.resize(1100, 750)
        self.setStyleSheet(STYLESHEET)
        
        self._init_ui()
        self._init_network()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 1. 左侧：画板区
        left_layout = QVBoxLayout()
        
        # 顶部提示栏
        self.lbl_info = QLabel("等待连接...")
        self.lbl_info.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        self.lbl_info.setAlignment(Qt.AlignCenter)
        self.lbl_info.setFixedHeight(40)
        
        # 画板
        self.draw_widget = DrawWidget()
        # 给画板加个边框阴影效果
        draw_container = QFrame()
        draw_container.setFrameShape(QFrame.StyledPanel)
        draw_container.setStyleSheet("background-color: white; border: 1px solid #ccc; border-radius: 4px;")
        draw_l = QVBoxLayout(draw_container)
        draw_l.setContentsMargins(0,0,0,0)
        draw_l.addWidget(self.draw_widget)

        left_layout.addWidget(self.lbl_info)
        left_layout.addWidget(draw_container, 1) # Stretch factor 1
        
        # 2. 右侧：交互区
        right_panel = QWidget()
        right_panel.setFixedWidth(320)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0,0,0,0)

        # 玩家列表
        grp_players = QGroupBox("玩家列表")
        l_players = QVBoxLayout(grp_players)
        self.list_players = QListWidget()
        l_players.addWidget(self.list_players)
        right_layout.addWidget(grp_players, 2)

        # 聊天区域
        grp_chat = QGroupBox("聊天 / 猜词")
        l_chat = QVBoxLayout(grp_chat)
        self.text_chat = QTextEdit()
        self.text_chat.setReadOnly(True)
        l_chat.addWidget(self.text_chat)
        right_layout.addWidget(grp_chat, 3)

        # 底部工具栏 (画笔设置 + 输入 + 准备)
        self.control_panel = QWidget()
        ctrl_layout = QVBoxLayout(self.control_panel)
        
        # 画笔工具行
        row_tools = QHBoxLayout()
        self.btn_colors = []
        colors = [("#000000", "黑"), ("#FF0000", "红"), ("#0000FF", "蓝"), ("#00FF00", "绿")]
        for c_code, c_name in colors:
            btn = QPushButton("")
            btn.setObjectName("color_btn")
            btn.setFixedSize(25, 25)
            btn.setStyleSheet(f"background-color: {c_code};")
            btn.setToolTip(c_name)
            btn.clicked.connect(lambda _, c=c_code: self.draw_widget.set_pen_color(c))
            row_tools.addWidget(btn)
            self.btn_colors.append(btn)
        
        row_tools.addStretch()
        
        sizes = [(2, "细"), (5, "中"), (10, "粗")]
        for s_val, s_name in sizes:
            btn = QPushButton(s_name)
            btn.setFixedSize(30, 25)
            btn.setStyleSheet("padding: 2px;")
            btn.clicked.connect(lambda _, s=s_val: self.draw_widget.set_pen_width(s))
            row_tools.addWidget(btn)
        
        ctrl_layout.addLayout(row_tools)
        
        # 输入行
        row_input = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("在此输入...")
        self.input_edit.returnPressed.connect(self.on_send)
        self.btn_send = QPushButton("发送")
        self.btn_send.setObjectName("btn_send")
        self.btn_send.clicked.connect(self.on_send)
        
        row_input.addWidget(self.input_edit)
        row_input.addWidget(self.btn_send)
        ctrl_layout.addLayout(row_input)
        
        # 准备按钮
        self.btn_ready = QPushButton("准备 (Ready)")
        self.btn_ready.setObjectName("btn_ready")
        self.btn_ready.setFixedHeight(40)
        self.btn_ready.clicked.connect(self.on_ready_clicked)
        ctrl_layout.addWidget(self.btn_ready)

        right_layout.addWidget(self.control_panel)

        # 主布局合并
        main_layout.addLayout(left_layout, 3)
        main_layout.addWidget(right_panel, 0)
        
        # 初始状态：画板不可用，画笔工具禁用
        self.draw_widget.set_interactive(False)
        self.control_panel.setEnabled(True)

        # 信号连接
        self.draw_widget.local_draw.connect(self.on_local_draw)

    def _init_network(self):
        self.net = NetworkClient(self.host, self.port)
        self.net.connected.connect(self.on_connected)
        self.net.disconnected.connect(self.on_disconnected)
        self.net.message_received.connect(self.on_msg)
        self.net.error_occurred.connect(lambda e: self.sys_msg(f"网络错误: {e}"))
        self.net.start()

    # ---- 逻辑处理 ----

    def sys_msg(self, text):
        """显示系统消息"""
        self.text_chat.append(f"<span style='color:#888'>[系统] {text}</span>")

    def chat_msg(self, sender, text):
        """显示聊天消息"""
        color = "#0052cc" if sender == self.player_name else "#333"
        self.text_chat.append(f"<span style='color:{color}'><b>{sender}:</b> {text}</span>")

    def update_player_list(self):
        """刷新列表显示"""
        self.list_players.clear()
        # 排序：分数高在前
        sorted_players = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        for name, score in sorted_players:
            status = " [已准备]" if self.ready_status.get(name) else ""
            if self.game_running:
                status = " [画画]" if name == self.current_drawer_name else " [猜词]"
            
            display = f"{name} : {score}分{status}"
            self.list_players.addItem(display)

    def set_game_ui_state(self, is_drawer):
        self.is_drawer = is_drawer
        self.draw_widget.set_interactive(is_drawer)
        
        # 只有画手能用画笔工具
        for btn in self.btn_colors:
            btn.setEnabled(is_drawer)
        
        if is_drawer:
            self.input_edit.setPlaceholderText("你是画手，不能聊天/猜词")
            self.input_edit.setEnabled(False)
            self.btn_send.setEnabled(False)
        else:
            self.input_edit.setPlaceholderText("输入答案或聊天...")
            self.input_edit.setEnabled(True)
            self.btn_send.setEnabled(True)

    # ---- 网络回调 ----

    def on_connected(self):
        self.lbl_info.setText("连接成功，请设置昵称...")
        name, ok = QInputDialog.getText(self, "欢迎", "请输入你的昵称：")
        if not ok or not name.strip():
            name = "Player"
        self.player_name = name.strip()
        self.net.send_message({"type": MSG_SET_NAME, "name": self.player_name})

    def on_disconnected(self):
        self.lbl_info.setText("服务器已断开")
        self.sys_msg("与服务器断开连接")
        self.control_panel.setEnabled(False)

    def on_msg(self, msg):
        mtype = msg.get("type")

        if mtype == MSG_WELCOME:
            self.sys_msg(f"欢迎加入！当前在线人数：{len(msg.get('players', []))}")
            self.lbl_info.setText(f"我是：{self.player_name}")
            
            # 初始化数据
            p_list = msg.get("players", [])
            self.scores = {p['name']: p['score'] for p in p_list}
            self.ready_status = {p['name']: p['is_ready'] for p in p_list}
            self.game_running = msg.get("in_game", False)
            self.current_drawer_name = msg.get("drawer")
            
            self.update_player_list()
            
            # 如果中途加入且游戏正在进行
            if self.game_running:
                self.btn_ready.setEnabled(False)
                self.set_game_ui_state(False) # 中途加入只能看
                self.sys_msg(f"游戏正在进行中，当前画手：{self.current_drawer_name}")

        elif mtype == MSG_PLAYER_JOIN:
            name = msg.get("player_name")
            self.scores[name] = 0
            self.ready_status[name] = False
            self.sys_msg(f"{name} 加入了游戏")
            self.update_player_list()

        elif mtype == MSG_PLAYER_LEAVE:
            name = msg.get("player_name")
            if name in self.scores:
                del self.scores[name]
            if name in self.ready_status:
                del self.ready_status[name]
            self.sys_msg(f"{name} 离开了游戏")
            self.update_player_list()

        elif mtype == MSG_SYSTEM:
            text = msg.get("text")
            self.sys_msg(text)
            # 简单的判断：如果消息包含"已准备"，则更新UI（虽不严谨但够用）
            if "已准备" in text:
                # 重新请求列表太麻烦，这里简单假设是单向增加
                # 实际最好 Server 广播 update_player_list
                # 这里为了简化，我们依赖 MSG_ROUND_START 清空状态
                pass

        elif mtype == MSG_CHAT:
            self.chat_msg(msg.get("from"), msg.get("text"))

        elif mtype == MSG_ROUND_START:
            self.game_running = True
            drawer = msg.get("drawer")
            hint = msg.get("hint")
            round_id = msg.get("round")
            self.current_drawer_name = drawer
            
            # 重置画板
            self.draw_widget.clear_canvas()
            
            # 重置准备状态
            for k in self.ready_status: 
                self.ready_status[k] = False
            self.btn_ready.setText("游戏中...")
            self.btn_ready.setEnabled(False)
            
            is_me = (drawer == self.player_name)
            self.set_game_ui_state(is_me)
            
            self.sys_msg(f"======== 第 {round_id} 轮开始 ========")
            self.sys_msg(f"画手：{drawer} | 提示：{hint}")
            self.lbl_info.setText(f"正在画：{drawer} | 提示：{hint}")
            
            self.update_player_list()

        elif mtype == MSG_ASSIGN_WORD:
            word = msg.get("word")
            QMessageBox.information(self, "你的题目", f"你要画的词是：\n\n【{word}】\n\n请在画板上画出来！")
            self.lbl_info.setText(f"题目：{word} (你正在画)")

        elif mtype == MSG_DRAW:
            self.draw_widget.draw_remote_line(msg.get("data"))

        elif mtype == MSG_ROUND_RESULT:
            winner = msg.get("winner")
            ans = msg.get("answer")
            new_scores = msg.get("scores")
            
            self.scores = new_scores
            self.game_running = False
            self.set_game_ui_state(False) # 大家都停笔
            self.input_edit.setEnabled(True) # 恢复输入框
            self.btn_send.setEnabled(True)
            
            msg_box = f"恭喜 {winner} 猜对了！\n答案是：{ans}"
            self.sys_msg(msg_box)
            QMessageBox.information(self, "本轮结束", msg_box)
            
            self.btn_ready.setText("准备 (Ready)")
            self.btn_ready.setEnabled(True)
            self.lbl_info.setText("请点击准备开始下一轮")
            self.update_player_list()

    # ---- 交互动作 ----

    def on_ready_clicked(self):
        self.net.send_message({"type": MSG_READY})
        self.btn_ready.setText("已准备")
        self.btn_ready.setEnabled(False)
        self.ready_status[self.player_name] = True
        self.update_player_list()

    def on_send(self):
        text = self.input_edit.text().strip()
        if not text: return
        self.input_edit.clear()
        
        if self.game_running and not self.is_drawer:
            # 游戏中且不是画手 -> 猜词
            self.net.send_message({"type": MSG_GUESS, "text": text})
        else:
            # 否则 -> 聊天
            self.net.send_message({"type": MSG_CHAT, "text": text})

    def on_local_draw(self, data):
        # 转发给服务器
        self.net.send_message({"type": MSG_DRAW, "data": data})

    def closeEvent(self, event):
        self.net.stop()
        self.net.wait(1000)
        super().closeEvent(event)