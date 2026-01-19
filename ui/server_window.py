import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTextEdit, QSplitter, 
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox, QGroupBox, QLineEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QIcon

try:
    import pyqtgraph as pg
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False

from ui.theme import ThemeManager, SpaceTheme

class StatusLed(QWidget):
    """Custom LED Indicator for Server Status"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self._active = False
        self.setToolTip("服务状态")
        
    def set_status(self, active: bool):
        self._active = active
        self.update()
        self.setToolTip("服务运行中" if active else "服务已停止")
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Color: Green (Active) or Red (Inactive)
        # Using simple colors or theme
        color = "#22C55E" if self._active else "#EF4444" 
        
        # Glow effect (outer ring opacity)
        if self._active:
            painter.setBrush(QBrush(QColor(color)))
            painter.setOpacity(0.3)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, 24, 24)
            painter.setOpacity(1.0)
        
        # Core
        painter.setBrush(QBrush(QColor(color)))
        painter.setPen(Qt.PenStyle.NoPen)
        center = 12
        radius = 6
        painter.drawEllipse(center - radius, center - radius, radius * 2, radius * 2)

class GraphsPanel(QWidget):
    """Panel containing real-time performance charts"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Background fallback
        self.setStyleSheet(f"background-color: {SpaceTheme.CHART_BG}; border-radius: 8px;")
        
        if not HAS_PYQTGRAPH:
            self._setup_placeholder()
            return

        # Configure PyQtGraph global options for Space Theme
        pg.setConfigOption('background', SpaceTheme.CHART_BG)
        pg.setConfigOption('foreground', SpaceTheme.TEXT_SECONDARY)
        pg.setConfigOptions(antialias=True)
        
        self.graph_widget = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.graph_widget)
        
        # Plot 1: Message Rate
        self.p1 = self.graph_widget.addPlot(title="消息速率 (msg/s)")
        self.p1.showGrid(x=True, y=True, alpha=0.3)
        self.curve1 = self.p1.plot(pen=pg.mkPen(color=SpaceTheme.CHART_LINE_1, width=2))
        
        # Plot 2: AI Requests
        self.graph_widget.nextRow()
        self.p2 = self.graph_widget.addPlot(title="AI 请求频率 (req/min)")
        self.p2.showGrid(x=True, y=True, alpha=0.3)
        self.curve2 = self.p2.plot(pen=pg.mkPen(color=SpaceTheme.CHART_LINE_2, width=2))
        
        # Data buffers
        self.data_limit = 60
        self.rate_history = [0] * self.data_limit
        self.ai_history = [0] * self.data_limit

    def _setup_placeholder(self):
        container = QFrame()
        vbox = QVBoxLayout(container)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_text = QLabel("图表组件未安装")
        lbl_text.setStyleSheet(f"color: {SpaceTheme.TEXT_DISABLED}; font-size: 16px; font-weight: bold;")
        lbl_msg = QLabel("请运行: pip install pyqtgraph")
        lbl_msg.setStyleSheet(f"color: {SpaceTheme.TEXT_DISABLED}; font-size: 12px;")
        
        vbox.addWidget(lbl_text)
        vbox.addWidget(lbl_msg)
        self.layout.addWidget(container)

    def update_charts(self, msg_rate, ai_rate):
        if not HAS_PYQTGRAPH: return
        
        self.rate_history.append(msg_rate)
        self.rate_history = self.rate_history[-self.data_limit:]
        
        self.ai_history.append(ai_rate)
        self.ai_history = self.ai_history[-self.data_limit:]
        
        self.curve1.setData(self.rate_history)
        self.curve2.setData(self.ai_history)

class ServerMainWindow(QMainWindow):
    """
    Modern Server Dashboard with Deep Space Theme (Localized).
    """
    start_server_requested = pyqtSignal(int)
    stop_server_requested = pyqtSignal()
    api_config_changed = pyqtSignal(str, str, str)
    disconnect_user_requested = pyqtSignal(str)
    
    # Optional signals
    refresh_stats_requested = pyqtSignal()
    test_ai_requested = pyqtSignal(str, str, str)
    
    def __init__(self):
        super().__init__()
        
        # Force Space Theme
        ThemeManager.set_theme("space")
        self.theme = SpaceTheme
        
        self.setWindowTitle("PetChat 服务端控制台 [Core]")
        self.resize(1000, 750)
        self.setStyleSheet(self.theme.get_stylesheet())
        
        self.setup_ui()
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # --- Header Section (Redesigned) ---
        header = QFrame()
        header.setFixedHeight(60)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title (Left)
        title_label = QLabel("PetChat 服务端")
        title_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {self.theme.PRIMARY}; font-family: 'Segoe UI', 'Microsoft YaHei';")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Status Area (Right)
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0,0,0,0)
        status_layout.setSpacing(12)
        
        self.status_led = StatusLed()
        status_layout.addWidget(self.status_led)
        
        self.status_label = QLabel("离线")
        self.status_label.setStyleSheet(f"color: {self.theme.TEXT_SECONDARY}; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        # Buttons
        self.btn_start = QPushButton("启动服务")
        self.btn_start.setFixedWidth(100)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self.on_start_clicked)
        status_layout.addWidget(self.btn_start)
        
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setFixedWidth(80)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setStyleSheet(f"background-color: {self.theme.ERROR}; border-color: {self.theme.ERROR};")
        self.btn_stop.clicked.connect(self.on_stop_clicked)
        self.btn_stop.setEnabled(False)
        status_layout.addWidget(self.btn_stop)
        
        header_layout.addWidget(status_container)
        main_layout.addWidget(header)
        
        # --- Splitter Section ---
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(2)
        main_layout.addWidget(splitter)
        
        # Top: Graphs
        self.graphs_panel = GraphsPanel()
        self.graphs_panel.setMinimumHeight(240)
        splitter.addWidget(self.graphs_panel)
        
        # Bottom: Tabs
        tabs = QTabWidget()
        tabs.setObjectName("right_sidebar")
        splitter.addWidget(tabs)
        
        # Tab 1: Logs
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setStyleSheet(f"""
            font-family: Consolas, 'Courier New', monospace; 
            font-size: 13px; 
            background-color: {self.theme.BG_ELEVATED}; 
            color: {self.theme.TEXT_SECONDARY}; 
            border: 1px solid {self.theme.BG_BORDER};
            padding: 8px;
        """)
        tabs.addTab(self.log_viewer, "系统日志")
        
        # Tab 2: Clients
        self.clients_table = QTableWidget()
        self.clients_table.setColumnCount(4)
        self.clients_table.setHorizontalHeaderLabels(["用户 ID", "昵称", "IP 地址", "加入时间"])
        self.clients_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.clients_table.verticalHeader().setVisible(False)
        self.clients_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.clients_table.setStyleSheet(f"background-color: {self.theme.BG_ELEVATED}; border: none;")
        tabs.addTab(self.clients_table, "在线客户端")
        
        # Tab 3: Configuration (Redesigned)
        config_tab = QWidget()
        config_layout = QVBoxLayout(config_tab)
        config_layout.setContentsMargins(20, 20, 20, 20)
        config_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Server Settings
        server_grp = QGroupBox("基础设置")
        server_grp.setStyleSheet(f"QGroupBox {{ color: {self.theme.PRIMARY}; font-weight: bold; border: 1px solid {self.theme.BG_BORDER}; border-radius: 6px; margin-top: 20px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}")
        svr_grid = QGridLayout(server_grp)
        
        svr_grid.addWidget(QLabel("服务端口:"), 0, 0)
        self.port_input = QLineEdit("8888")
        self.port_input.setFixedWidth(120)
        svr_grid.addWidget(self.port_input, 0, 1)
        svr_grid.setColumnStretch(2, 1) # Spacer
        
        config_layout.addWidget(server_grp)
        
        # AI Settings
        ai_grp = QGroupBox("AI 模型配置")
        ai_grp.setStyleSheet(server_grp.styleSheet())
        ai_grid = QGridLayout(ai_grp)
        ai_grid.setVerticalSpacing(12)
        
        ai_grid.addWidget(QLabel("API 密钥:"), 0, 0)
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("sk-...")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        ai_grid.addWidget(self.api_key_input, 0, 1)
        
        ai_grid.addWidget(QLabel("接口地址:"), 1, 0)
        self.api_base_input = QLineEdit()
        self.api_base_input.setPlaceholderText("https://api.openai.com/v1")
        ai_grid.addWidget(self.api_base_input, 1, 1)
        
        ai_grid.addWidget(QLabel("模型名称:"), 2, 0)
        self.model_input = QLineEdit("gpt-4o-mini")
        ai_grid.addWidget(self.model_input, 2, 1)
        
        config_layout.addWidget(ai_grp)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)
        
        btn_apply = QPushButton("应用配置")
        btn_apply.setFixedWidth(120)
        btn_apply.clicked.connect(self.on_apply_config)
        btn_layout.addWidget(btn_apply)
        
        btn_test = QPushButton("测试连接")
        btn_test.setFixedWidth(120)
        btn_test.setStyleSheet(f"background-color: {self.theme.BG_SURFACE}; border: 1px solid {self.theme.PRIMARY}; color: {self.theme.PRIMARY};")
        btn_test.clicked.connect(self.on_test_ai)
        btn_layout.addWidget(btn_test)
        
        btn_layout.addStretch()
        config_layout.addLayout(btn_layout)
        
        tabs.addTab(config_tab, "设置")

        # Tab 4: Statistics
        self.stats_label = QLabel("等待服务启动...")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.stats_label.setStyleSheet("padding: 20px; font-size: 14px; line-height: 1.5;")
        tabs.addTab(self.stats_label, "统计信息")
        
        splitter.setSizes([280, 470])

    def on_apply_config(self):
        self.api_config_changed.emit(
            self.api_key_input.text(),
            self.api_base_input.text(),
            self.model_input.text()
        )
        QMessageBox.information(self, "配置已保存", "AI 配置已更新并保存。")
        
    def on_test_ai(self):
        self.test_ai_requested.emit(
            self.api_key_input.text(),
            self.api_base_input.text(),
            self.model_input.text()
        )

    def show_ai_result(self, message, is_success):
        if is_success:
             QMessageBox.information(self, "测试通过", message)
        else:
             QMessageBox.warning(self, "测试失败", message)

    def on_start_clicked(self):
        try:
            port = int(self.port_input.text())
            self.start_server_requested.emit(port)
        except ValueError:
            QMessageBox.warning(self, "输入错误", "端口必须是数字")
        
    def on_stop_clicked(self):
        self.stop_server_requested.emit()

    def update_server_status(self, running: bool):
        self.status_led.set_status(running)
        if running:
            self.status_label.setText("运行中")
            self.status_label.setStyleSheet(f"color: {self.theme.SUCCESS}; font-weight: bold;")
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.log_message("服务状态: 运行中")
        else:
            self.status_label.setText("已停止")
            self.status_label.setStyleSheet(f"color: {self.theme.TEXT_SECONDARY}; font-weight: bold;")
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.log_message("服务状态: 已停止")

    def log_message(self, message: str):
        from datetime import datetime
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.log_viewer.append(f"{timestamp} {message}")
        cursor = self.log_viewer.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_viewer.setTextCursor(cursor)

    def update_stats(self, msg_count, ai_req_count):
        current_text = self.stats_label.text().split("\n\nToken Usage:")[0] # English legacy check
        if "Token Usage" not in current_text and "Token 消耗" not in current_text:
             # Basic update
             pass
             
        # Reconstruct
        token_part = ""
        if "Token 消耗" in self.stats_label.text():
             token_part = "\n\n" + self.stats_label.text().split("\n\nToken 消耗")[1]
        
        self.stats_label.setText(
            f"已处理消息总数: {msg_count}\n"
            f"AI 请求总数: {ai_req_count}"
            f"{token_part}"
        )

    def update_token_stats(self, usage_dict):
        """Update token usage statistics"""
        current_text = self.stats_label.text()
        base_stats = current_text.split("\n\nToken 消耗")[0]
        
        token_text = "\n\nToken 消耗:\n"
        for model, usage in usage_dict.items():
            token_text += f"  {model}: {usage} tokens\n"
            
        self.stats_label.setText(base_stats + token_text)
    
    def update_charts(self, msg_rate, ai_rate):
        self.graphs_panel.update_charts(msg_rate, ai_rate)
        
    def add_client(self, user_id, name, address):
        row = self.clients_table.rowCount()
        self.clients_table.insertRow(row)
        self.clients_table.setItem(row, 0, QTableWidgetItem(user_id))
        self.clients_table.setItem(row, 1, QTableWidgetItem(name))
        ip_str = f"{address[0]}:{address[1]}" if isinstance(address, tuple) else str(address)
        self.clients_table.setItem(row, 2, QTableWidgetItem(ip_str))
        from datetime import datetime
        self.clients_table.setItem(row, 3, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
        self.log_message(f"客户端加入: {name} ({ip_str})")
        
    def remove_client(self, user_id):
        # Find row
        for row in range(self.clients_table.rowCount()):
            item = self.clients_table.item(row, 0)
            if item and item.text() == user_id:
                name = self.clients_table.item(row, 1).text()
                self.clients_table.removeRow(row)
                self.log_message(f"客户端断开: {name}")
                break
