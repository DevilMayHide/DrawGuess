import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QListWidget, QLabel,
    QMessageBox, QGroupBox, QFrame, QGraphicsDropShadowEffect,
    QDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

# 引入之前的模块
from draw_widget import DrawWidget
from network import NetworkClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from Shared.protocol import *

# ==========================================
#   样式表 (Updated)
# ==========================================
GAME_STYLESHEET = """
QMainWindow { background-color: #1e1e2e; }
QLabel { color: #cdd6f4; font-family: "Microsoft YaHei UI", sans-serif; }
QLabel#header_title { font-size: 24px; font-weight: bold; color: #f5c2e7; padding: 10px; }
QLabel#status_label { color: #a6adc8; font-style: italic; }

/* 容器样式 */
QGroupBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 12px;
    margin-top: 10px;
    color: #cdd6f4;
    font-weight: bold;
    font-size: 14px;
}
QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; color: #89b4fa; }

/* 列表和文本框 */
QListWidget, QTextEdit {
    background-color: #181825; border: 1px solid #45475a; border-radius: 8px;
    color: #cdd6f4; padding: 5px; font-size: 14px;
}
QLineEdit {
    background-color: #181825; border: 2px solid #45475a; border-radius: 20px;
    color: #cdd6f4; padding: 8px 15px; font-size: 14px;
}
QLineEdit:focus { border: 2px solid #89b4fa; }

/* 按钮通用样式 */
QPushButton {
    background-color: #45475a; color: white; border-radius: 8px; padding: 8px 16px;
    font-weight: bold; font-family: "Microsoft YaHei UI"; border: none;
}
QPushButton:hover { background-color: #585b70; margin-top: -2px; margin-bottom: 2px; }
QPushButton:pressed { background-color: #313244; margin-top: 2px; margin-bottom: -2px; }
QPushButton:disabled { background-color: #313244; color: #6c7086; }

/* 特殊功能按钮 */
QPushButton#btn_send { background-color: #89b4fa; color: #1e1e2e; }
QPushButton#btn_send:hover { background-color: #b4befe; }

QPushButton#btn_ready {
    background-color: #a6e3a1; color: #1e1e2e; font-size: 16px;
    border-bottom: 4px solid #589656; border-radius: 10px;
}
QPushButton#btn_ready:hover { background-color: #94e2d5; }
QPushButton#btn_ready:pressed { border-bottom: 0px; margin-top: 4px; }
QPushButton#btn_ready:disabled { background-color: #313244; border-bottom: none; color: #a6adc8; }

/* 工具栏小按钮 */
QPushButton.tool_btn { font-size: 14px; padding: 5px 10px; }
QPushButton#btn_clear { background-color: #e78284; color: #1e1e2e; } /* 红色清空 */
QPushButton#btn_undo { background-color: #f9e2af; color: #1e1e2e; }  /* 黄色撤销 */
QPushButton#btn_eraser { background-color: #cdd6f4; color: #1e1e2e; } /* 白色橡皮 */

QPushButton.color_btn { border: 2px solid #fff; border-radius: 12px; }
QPushButton.color_btn:hover { border: 3px solid #f5c2e7; }
"""

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("创建角色")
        self.setFixedSize(400, 250)
        self.name = "Player"
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; font-size: 16px; }
            QLineEdit { 
                background-color: #313244; border: 2px solid #45475a; border-radius: 8px;
                color: #f5c2e7; padding: 10px; font-size: 18px; font-weight: bold;
            }
            QLineEdit:focus { border: 2px solid #cba6f7; }
            QPushButton {
                background-color: #cba6f7; color: #1e1e2e; border-radius: 8px;
                padding: 10px; font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #f5c2e7; }
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        title = QLabel("👾 请输入你的昵称")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #cba6f7;")
        layout.addWidget(title)
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("例如: 绘画大师")
        self.input_name.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.input_name)
        btn_confirm = QPushButton("进入游戏")
        btn_confirm.setCursor(Qt.PointingHandCursor)
        btn_confirm.clicked.connect(self.accept_input)
        layout.addWidget(btn_confirm)

    def accept_input(self):
        txt = self.input_name.text().strip()
        if txt:
            self.name = txt
            self.accept()
        else:
            self.input_name.setPlaceholderText("昵称不能为空！")

class MainWindow(QMainWindow):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.player_name = ""
        self.is_drawer = False
        self.game_running = False
        self.scores = {} 
        self.ready_status = {}

        self.setWindowTitle("DrawGuess - 你画我猜 Online")
        self.resize(1200, 800)
        self.setStyleSheet(GAME_STYLESHEET)
        
        self._init_ui()
        self._init_network()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        global_layout = QVBoxLayout(central)
        global_layout.setContentsMargins(20, 10, 20, 20)
        global_layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("🎨 DRAW & GUESS")
        title_label.setObjectName("header_title")
        self.lbl_info = QLabel("正在连接服务器...")
        self.lbl_info.setObjectName("status_label")
        self.lbl_info.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_info)
        global_layout.addLayout(header_layout)

        # Content
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Left: Canvas
        self.canvas_container = QFrame()
        self.canvas_container.setObjectName("canvas_container")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        self.canvas_container.setGraphicsEffect(shadow)
        self.canvas_container.setStyleSheet("QFrame#canvas_container { background-color: #45475a; border-radius: 8px; }")

        canvas_layout = QVBoxLayout(self.canvas_container)
        canvas_layout.setContentsMargins(10, 10, 10, 10)
        
        self.draw_widget = DrawWidget()
        canvas_layout.addWidget(self.draw_widget)
        content_layout.addWidget(self.canvas_container, stretch=3)

        # Right: Sidebar
        sidebar_widget = QWidget()
        sidebar_widget.setFixedWidth(350)
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(15)

        grp_players = QGroupBox("🏆 玩家排行榜")
        l_players = QVBoxLayout(grp_players)
        self.list_players = QListWidget()
        self.list_players.setFocusPolicy(Qt.NoFocus)
        l_players.addWidget(self.list_players)
        sidebar_layout.addWidget(grp_players, stretch=2)

        grp_chat = QGroupBox("💬 消息频道")
        l_chat = QVBoxLayout(grp_chat)
        self.text_chat = QTextEdit()
        self.text_chat.setReadOnly(True)
        self.text_chat.setFocusPolicy(Qt.NoFocus)
        l_chat.addWidget(self.text_chat)
        sidebar_layout.addWidget(grp_chat, stretch=3)

        ctrl_panel = QWidget()
        ctrl_layout = QVBoxLayout(ctrl_panel)
        ctrl_layout.setContentsMargins(0, 10, 0, 0)
        
        # === 工具栏区域 (Updated) ===
        self.tool_widget = QWidget()
        tool_layout = QVBoxLayout(self.tool_widget) # 改为垂直布局包含两行
        tool_layout.setContentsMargins(0, 0, 0, 0)
        tool_layout.setSpacing(8)

        # 第一行：颜色和粗细
        row1 = QHBoxLayout()
        colors = [("#1e1e2e", "黑"), ("#e78284", "红"), ("#89b4fa", "蓝"), ("#a6e3a1", "绿"), ("#f9e2af", "黄"), ("#cba6f7", "紫")]
        for c_code, c_name in colors:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setProperty("class", "color_btn")
            btn.setStyleSheet(f"background-color: {c_code}; border-radius: 12px;")
            btn.setToolTip(c_name)
            btn.clicked.connect(lambda _, c=c_code: self.draw_widget.set_pen_color(c))
            row1.addWidget(btn)
        
        row1.addStretch()
        
        sizes = [(2, "•"), (5, "●"), (10, "⬤")]
        for s_val, s_text in sizes:
            btn = QPushButton(s_text)
            btn.setFixedSize(30, 30)
            btn.clicked.connect(lambda _, s=s_val: self.draw_widget.set_pen_width(s))
            row1.addWidget(btn)
        
        tool_layout.addLayout(row1)

        # 第二行：橡皮、撤销、清空
        row2 = QHBoxLayout()
        
        self.btn_eraser = QPushButton("🧼 橡皮")
        self.btn_eraser.setObjectName("btn_eraser")
        self.btn_eraser.setProperty("class", "tool_btn")
        self.btn_eraser.clicked.connect(self.draw_widget.set_eraser_mode)
        
        self.btn_undo = QPushButton("↩️ 撤销")
        self.btn_undo.setObjectName("btn_undo")
        self.btn_undo.setProperty("class", "tool_btn")
        self.btn_undo.clicked.connect(self.draw_widget.undo)

        self.btn_clear = QPushButton("🗑️ 清空")
        self.btn_clear.setObjectName("btn_clear")
        self.btn_clear.setProperty("class", "tool_btn")
        self.btn_clear.clicked.connect(self.draw_widget.clear_all)

        row2.addWidget(self.btn_eraser)
        row2.addWidget(self.btn_undo)
        row2.addWidget(self.btn_clear)
        
        tool_layout.addLayout(row2)

        ctrl_layout.addWidget(self.tool_widget)
        # ==========================================

        input_row = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("在此输入答案...")
        self.input_edit.returnPressed.connect(self.on_send)
        self.btn_send = QPushButton("发送")
        self.btn_send.setObjectName("btn_send")
        self.btn_send.setFixedSize(60, 36)
        self.btn_send.setCursor(Qt.PointingHandCursor)
        self.btn_send.clicked.connect(self.on_send)
        input_row.addWidget(self.input_edit)
        input_row.addWidget(self.btn_send)
        ctrl_layout.addLayout(input_row)

        self.btn_ready = QPushButton("🎮 准备开始 (READY)")
        self.btn_ready.setObjectName("btn_ready")
        self.btn_ready.setFixedHeight(50)
        self.btn_ready.setCursor(Qt.PointingHandCursor)
        self.btn_ready.clicked.connect(self.on_ready_clicked)
        ctrl_layout.addWidget(self.btn_ready)

        sidebar_layout.addWidget(ctrl_panel)
        content_layout.addWidget(sidebar_widget, stretch=0)
        global_layout.addLayout(content_layout)

        self.draw_widget.set_interactive(False)
        self.tool_widget.setVisible(False)
        self.draw_widget.local_draw.connect(self.on_local_draw)

    def _init_network(self):
        self.net = NetworkClient(self.host, self.port)
        self.net.connected.connect(self.on_connected)
        self.net.disconnected.connect(self.on_disconnected)
        self.net.message_received.connect(self.on_msg)
        self.net.error_occurred.connect(lambda e: self.sys_msg(f"❌ 网络错误: {e}"))
        self.net.start()

    def sys_msg(self, text):
        self.text_chat.append(f"<span style='color:#a6adc8; font-style:italic;'>[系统] {text}</span>")

    def chat_msg(self, sender, text):
        color = "#89b4fa" if sender == self.player_name else "#f5c2e7"
        self.text_chat.append(f"<span style='color:{color}; font-weight:bold;'>{sender}:</span> <span style='color:#cdd6f4'>{text}</span>")

    def update_player_list(self):
        self.list_players.clear()
        sorted_players = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        for name, score in sorted_players:
            status_icon = "⚪"
            if self.ready_status.get(name): status_icon = "🟢"
            if self.game_running:
                if name == self.current_drawer_name: status_icon = "🎨"
                else: status_icon = "🤔"
            display_text = f"{status_icon} {name}  Points: {score}"
            if name == self.player_name: display_text += " (我)"
            self.list_players.addItem(display_text)

    def set_game_ui_state(self, is_drawer):
        self.is_drawer = is_drawer
        self.draw_widget.set_interactive(is_drawer)
        self.tool_widget.setVisible(is_drawer)
        if is_drawer:
            self.input_edit.setPlaceholderText("🚫 你是画手，请直接画图...")
            self.input_edit.setEnabled(False)
            self.btn_send.setEnabled(False)
        else:
            self.input_edit.setPlaceholderText("💡 输入你的猜测...")
            self.input_edit.setEnabled(True)
            self.btn_send.setEnabled(True)
            self.input_edit.setFocus()

    def on_connected(self):
        self.lbl_info.setText("✅ 已连接 | 验证中...")
        dlg = LoginDialog(self)
        if dlg.exec_():
            self.player_name = dlg.name
            self.net.send_message({"type": MSG_SET_NAME, "name": self.player_name})
        else:
            self.player_name = "Guest"
            self.net.send_message({"type": MSG_SET_NAME, "name": self.player_name})

    def on_disconnected(self):
        self.lbl_info.setText("❌ 服务器断开")
        self.sys_msg("与服务器断开连接")
        self.btn_ready.setEnabled(False)

    def on_msg(self, msg):
        mtype = msg.get("type")
        if mtype == MSG_WELCOME:
            p_list = msg.get("players", [])
            self.scores = {}
            self.ready_status = {}
            for p in p_list:
                if isinstance(p, dict):
                    name = p['name']
                    self.scores[name] = p['score']
                    self.ready_status[name] = p.get('is_ready', False)
                else:
                    self.scores[str(p)] = 0
                    self.ready_status[str(p)] = False
            self.game_running = msg.get("in_game", False)
            self.current_drawer_name = msg.get("drawer")
            self.sys_msg(f"加入房间成功！当前在线: {len(self.scores)}人")
            self.lbl_info.setText(f"👤 {self.player_name}")
            self.update_player_list()
            if self.game_running:
                self.btn_ready.setEnabled(False)
                self.btn_ready.setText("游戏进行中...")
                self.set_game_ui_state(False)

        elif mtype == MSG_PLAYER_JOIN:
            name = msg.get("player_name")
            self.scores[name] = 0
            self.ready_status[name] = False
            self.sys_msg(f"👋 {name} 加入了房间")
            self.update_player_list()

        elif mtype == MSG_PLAYER_LEAVE:
            name = msg.get("player_name")
            self.scores.pop(name, None)
            self.ready_status.pop(name, None)
            self.sys_msg(f"💨 {name} 离开了房间")
            self.update_player_list()

        elif mtype == MSG_SYSTEM:
            text = msg.get("text")
            self.sys_msg(text)

        elif mtype == MSG_CHAT:
            self.chat_msg(msg.get("from"), msg.get("text"))

        elif mtype == MSG_ROUND_START:
            self.game_running = True
            drawer = msg.get("drawer")
            hint = msg.get("hint")
            round_id = msg.get("round")
            self.current_drawer_name = drawer
            self.draw_widget.clear_all() # 新轮次彻底清空
            for k in self.ready_status: self.ready_status[k] = False
            self.btn_ready.setText(f"第 {round_id} 轮进行中")
            self.btn_ready.setEnabled(False)
            self.btn_ready.setStyleSheet("background-color: #fab387; border-bottom: 4px solid #d97e44;")
            is_me = (drawer == self.player_name)
            self.set_game_ui_state(is_me)
            self.text_chat.append(f"<br><center><b style='color:#f9e2af; font-size:14px;'>=== 第 {round_id} 轮开始 ===</b></center>")
            self.sys_msg(f"画手是: <b style='color:#f38ba8'>{drawer}</b> | 提示: {hint}")
            self.update_player_list()

        elif mtype == MSG_ASSIGN_WORD:
            word = msg.get("word")
            QMessageBox.information(self, "题目", f"🤫 嘘！你的题目是：\n\n【 {word} 】\n\n快画出来让大家猜！")
            self.lbl_info.setText(f"🎨 正在画: {word}")

        elif mtype == MSG_DRAW:
            self.draw_widget.draw_remote_line(msg.get("data"))

        elif mtype == MSG_ROUND_RESULT:
            winner = msg.get("winner")
            ans = msg.get("answer")
            self.scores = msg.get("scores")
            self.game_running = False
            self.set_game_ui_state(False)
            self.text_chat.append(f"<center><b style='color:#a6e3a1; font-size:15px;'>🎉 {winner} 猜对了！🎉</b></center>")
            self.text_chat.append(f"<center>答案是: <b style='color:#fab387'>{ans}</b></center><br>")
            self.btn_ready.setText("🎮 准备下一轮 (READY)")
            self.btn_ready.setEnabled(True)
            self.btn_ready.setStyleSheet("")
            self.update_player_list()

    def on_ready_clicked(self):
        self.net.send_message({"type": MSG_READY})
        self.btn_ready.setText("⏳ 已准备 (Waiting...)")
        self.btn_ready.setEnabled(False)
        self.btn_ready.setStyleSheet("background-color: #45475a; color: #a6adc8; border-bottom: none;")
        self.ready_status[self.player_name] = True
        self.update_player_list()

    def on_send(self):
        text = self.input_edit.text().strip()
        if not text: return
        self.input_edit.clear()
        if self.game_running and not self.is_drawer:
            self.net.send_message({"type": MSG_GUESS, "text": text})
        else:
            self.net.send_message({"type": MSG_CHAT, "text": text})

    def on_local_draw(self, data):
        self.net.send_message({"type": MSG_DRAW, "data": data})

    def closeEvent(self, event):
        self.net.stop()
        self.net.wait(1000)
        super().closeEvent(event)