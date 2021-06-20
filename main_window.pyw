import sys
import ctypes
import time
import traceback

from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QIcon, QCursor, QDesktopServices
from PyQt5.QtWidgets import (qApp, QApplication, QMainWindow, QWidget,
                             QPushButton, QLabel, QLineEdit, QMessageBox,
                             QSystemTrayIcon, QMenu, QAction, QGraphicsDropShadowEffect)
from filter_window import FilterWindow
from main import MainControl
from sys_helper import SysHelper
from iface_helper import get_tap_iface
from config_helper import load_config, save_config
from logger import LOGGER


VERSION_CODE = '4.0'
MAIN_DOMAIN = 'm.nxyexiong.xyz'
STYLE_SHEET = '''
#MainWidget{
    background-color: #312F30;
    border-top-left-radius:7px;
    border-top-right-radius:7px;
    border-bottom-left-radius:7px;
    border-bottom-right-radius:7px;
}
#CloseButton{
    background-color: #EE544A;
    border-radius: 5px;
}
#MinButton{
    background-color: #FDBD3F;
    border-radius: 5px;
}
#TitleLabel{
    font-family: "Consolas";
    color: #CCCCCC;
    font-size: 12px;
}
#NormalLabel{
    font-family: "Consolas";
    color: #DDDDDD;
    font-size: 14px;
}

QLineEdit{
    background-color: #505050;
    border: 0px;
    border-radius: 5px;
    color: #DDDDDD;
    font-family: "Consolas";
    font-size: 14px;
    padding-left: 5px;
    padding-right: 5px;
}
QLineEdit:focus{
    background-color: #BBBBBB;
    border: 0px;
    border-radius: 5px;
    color: #505050;
    font-family: "Consolas";
    font-size: 14px;
    padding-left: 5px;
    padding-right: 5px;
}
QPushButton{
    background-color: #1583F6;
    border-radius: 3px;
    color: #DDDDDD;
    padding: 5px 5px;
    text-align: center;
    font-size: 14px;
    font-family: "Consolas";
}
QPushButton:hover{
    background-color: #2593FF;
    border-radius: 3px;
    color: #DDDDDD;
    padding: 5px 5px;
    text-align: center;
    font-size: 14px;
    font-family: "Consolas";
}
QPushButton:pressed{
    background-color: #0573E6;
    border-radius: 3px;
    color: #DDDDDD;
    padding: 5px 5px;
    text-align: center;
    font-size: 14px;
    font-family: "Consolas";
}
QPushButton:disabled{
    background-color: #666465;
    border-radius: 3px;
    color: #DDDDDD;
    padding: 5px 5px;
    text-align: center;
    font-size: 14px;
    font-family: "Consolas";
}
'''


class FrontWindow(QMainWindow):
    m_drag = True
    m_DragPosition = None

    def __init__(self):
        super().__init__()

        self.running = False
        self.connected = False
        self.mainControl = MainControl()
        self.mainControl.set_connect_cb(self.mainConnectCallback)
        self.mainControl.set_tuntapset_cb(self.mainTuntapSetCallback)
        self.mainControl.set_tapcontrolset_cb(self.mainTapControlSetCallback)
        self.mainControl.set_stop_cb(self.mainStopCallback)

        self.initUI()
        self.initConfig()
        self.setTray()

        self.filterWindow = FilterWindow()

    def initUI(self):
        self.setGeometry(300, 300, 350, 333)
        self.setWindowTitle('Outernet')
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(QIcon('res/icon.png'))
        self.setStyleSheet(STYLE_SHEET)

        self.mainWidget = QWidget(self)
        self.mainWidget.setGeometry(7, 7, self.width() - 14, self.height() - 14)
        self.mainWidget.setObjectName('MainWidget')

        shadow = QGraphicsDropShadowEffect(self.mainWidget)
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 0)
        shadow.setColor(Qt.black)
        self.mainWidget.setGraphicsEffect(shadow)

        closeBtn = QPushButton('', self)
        closeBtn.resize(10, 10)
        closeBtn.clicked.connect(self.onClose)
        closeBtn.setObjectName('CloseButton')
        closeBtn.move(14, 14)

        minBtn = QPushButton('', self)
        minBtn.resize(10, 10)
        minBtn.clicked.connect(self.hide)
        minBtn.setObjectName('MinButton')
        minBtn.move(32, 14)

        titleLabel = QLabel('Outernet - %s' % (VERSION_CODE,), self)
        titleLabel.setObjectName('TitleLabel')
        titleLabel.adjustSize()
        titleLabel.move(350 / 2 - titleLabel.width() / 2, 14)  # 127

        addrLabel = QLabel('Server address', self)
        addrLabel.resize(112, 20)
        addrLabel.setObjectName('NormalLabel')
        addrLabel.move(30, 50)

        portLabel = QLabel('Server port', self)
        portLabel.resize(112, 20)
        portLabel.setObjectName('NormalLabel')
        portLabel.move(30, 77)

        userLabel = QLabel('User name', self)
        userLabel.resize(112, 20)
        userLabel.setObjectName('NormalLabel')
        userLabel.move(30, 104)

        secretLabel = QLabel('Secret', self)
        secretLabel.resize(112, 20)
        secretLabel.setObjectName('NormalLabel')
        secretLabel.move(30, 131)

        rxRateLabel = QLabel('Down rate', self)
        rxRateLabel.resize(112, 20)
        rxRateLabel.setObjectName('NormalLabel')
        rxRateLabel.move(30, 158)

        txRateLabel = QLabel('Up rate', self)
        txRateLabel.resize(112, 20)
        txRateLabel.setObjectName('NormalLabel')
        txRateLabel.move(30, 185)

        rxTotalLabel = QLabel('Down total', self)
        rxTotalLabel.resize(112, 20)
        rxTotalLabel.setObjectName('NormalLabel')
        rxTotalLabel.move(30, 212)

        txTotalLabel = QLabel('Up total', self)
        txTotalLabel.resize(112, 20)
        txTotalLabel.setObjectName('NormalLabel')
        txTotalLabel.move(30, 239)

        self.addrEdit = QLineEdit('', self)
        self.addrEdit.setAlignment(Qt.AlignRight)
        self.addrEdit.resize(160, 22)
        self.addrEdit.move(160, 49)

        self.portEdit = QLineEdit('', self)
        self.portEdit.setAlignment(Qt.AlignRight)
        self.portEdit.resize(160, 22)
        self.portEdit.move(160, 76)

        self.userEdit = QLineEdit('', self)
        self.userEdit.setAlignment(Qt.AlignRight)
        self.userEdit.resize(160, 22)
        self.userEdit.move(160, 103)

        self.secretEdit = QLineEdit('', self)
        self.secretEdit.setAlignment(Qt.AlignRight)
        self.secretEdit.resize(160, 22)
        self.secretEdit.move(160, 130)

        self.rxRateNumberLabel = QLabel('0.0 MB/s', self)
        self.rxRateNumberLabel.resize(160, 20)
        self.rxRateNumberLabel.setAlignment(Qt.AlignRight)
        self.rxRateNumberLabel.setObjectName('NormalLabel')
        self.rxRateNumberLabel.move(160, 158)

        self.txRateNumberLabel = QLabel('0.0 MB/s', self)
        self.txRateNumberLabel.resize(160, 20)
        self.txRateNumberLabel.setAlignment(Qt.AlignRight)
        self.txRateNumberLabel.setObjectName('NormalLabel')
        self.txRateNumberLabel.move(160, 185)

        self.rxTotalNumberLabel = QLabel('0.0 MB', self)
        self.rxTotalNumberLabel.resize(160, 20)
        self.rxTotalNumberLabel.setAlignment(Qt.AlignRight)
        self.rxTotalNumberLabel.setObjectName('NormalLabel')
        self.rxTotalNumberLabel.move(160, 212)

        self.txTotalNumberLabel = QLabel('0.0 MB', self)
        self.txTotalNumberLabel.resize(160, 20)
        self.txTotalNumberLabel.setAlignment(Qt.AlignRight)
        self.txTotalNumberLabel.setObjectName('NormalLabel')
        self.txTotalNumberLabel.move(160, 239)

        self.toggleConnectBtn = QPushButton("Connect", self)
        self.toggleConnectBtn.clicked.connect(self.toggleConnect)
        self.toggleConnectBtn.resize(230, 25)
        self.toggleConnectBtn.move(29, 278)

        self.toggleFilterBtn = QPushButton(self)
        self.toggleFilterBtn.setIcon(QIcon('res/filter.png'))
        self.toggleFilterBtn.clicked.connect(self.toggleFilter)
        self.toggleFilterBtn.resize(25, 25)
        self.toggleFilterBtn.move(264, 278)

        self.viewMainPageBtn = QPushButton(self)
        self.viewMainPageBtn.setIcon(QIcon('res/home.png'))
        self.viewMainPageBtn.clicked.connect(self.handleViewMainPage)
        self.viewMainPageBtn.resize(25, 25)
        self.viewMainPageBtn.move(294, 278)

        # set traffic timer
        self.trafficTimer = QTimer()
        self.trafficTimer.timeout.connect(self.handleTraffic)
        self.trafficTimer.start(1000)

        self.show()

    def initConfig(self):
        config = load_config()
        if config is not None:
            self.addrEdit.setText(str(config.get('addr')))
            self.portEdit.setText(str(config.get('port')))
            self.userEdit.setText(str(config.get('user')))
            self.secretEdit.setText(str(config.get('secret')))

    def onClose(self):
        self.show()
        if self.connected:
            quit_msg = "Exit the program after connected will cause serious problems. Continue exit?"
            reply = QMessageBox.question(self, 'Warning', quit_msg, QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.No:
                return
            self.mainControl.stop()
        self.close()
        qApp.quit()

    def setTray(self):
        self.tray = QSystemTrayIcon(QIcon('res/icon.png'), self)
        self.tray.activated.connect(self.trayEvent)
        self.trayMenu = QMenu(QApplication.desktop())
        self.RestoreAction = QAction('Open', self, triggered=self.show)
        self.ClearTrafficAction = QAction('Clear traffic info', self, triggered=self.handleClearTraffic)
        self.ViewMainPageAction = QAction('View main page', self, triggered=self.handleViewMainPage)
        self.FixAction = QAction('Fix', self, triggered=self.handleFix)
        self.QuitAction = QAction('Quit', self, triggered=self.onClose)
        self.trayMenu.addAction(self.RestoreAction)
        self.trayMenu.addAction(self.ClearTrafficAction)
        self.trayMenu.addAction(self.ViewMainPageAction)
        self.trayMenu.addAction(self.FixAction)
        self.trayMenu.addAction(self.QuitAction)
        self.tray.setContextMenu(self.trayMenu)
        self.tray.setToolTip(self.getTooltips())
        self.tray.show()

    def getTooltips(self):
        tooltips = 'Outernet - %s' % (VERSION_CODE,)
        if self.connected:
            tooltips += "\n(connected)\n"
            tooltips += "Server: " + self.addrEdit.text() + ":" + self.portEdit.text()
        else:
            tooltips += "\n(disconnected)"
        return tooltips

    def trayEvent(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()

    def toggleConnect(self):
        if not self.running:
            server_ip = self.addrEdit.text()
            server_port = self.portEdit.text()
            username = self.userEdit.text()
            secret = self.secretEdit.text()
            try:
                server_port = int(server_port)
            except Exception:
                return

            # save config
            config = {}
            config['addr'] = server_ip
            config['port'] = server_port
            config['user'] = username
            config['secret'] = secret
            save_config(config)

            self.running = True
            self.toggleConnectBtn.setText('Connecting...')
            self.toggleConnectBtn.setEnabled(False)
            self.addrEdit.setEnabled(False)
            self.portEdit.setEnabled(False)
            self.userEdit.setEnabled(False)
            self.secretEdit.setEnabled(False)
            self.mainControl.run(server_ip, server_port, username, secret)
        else:
            self.toggleConnectBtn.setText('Stopping...')
            self.toggleConnectBtn.setEnabled(False)
            self.mainControl.stop()

    def toggleFilter(self):
        self.filterWindow.show()

    def handleTraffic(self):
        rxRate = self.mainControl.get_rx_rate()
        txRate = self.mainControl.get_tx_rate()
        rxTotal = self.mainControl.get_rx_total()
        txTotal = self.mainControl.get_tx_total()
        rxRate = int((rxRate / (1024 * 1024)) * 10) / 10
        txRate = int((txRate / (1024 * 1024)) * 10) / 10
        rxTotal = int((rxTotal / (1024 * 1024)) * 10) / 10
        txTotal = int((txTotal / (1024 * 1024)) * 10) / 10
        self.rxRateNumberLabel.setText(str(rxRate) + ' MB/s')
        self.txRateNumberLabel.setText(str(txRate) + ' MB/s')
        self.rxTotalNumberLabel.setText(str(rxTotal) + ' MB')
        self.txTotalNumberLabel.setText(str(txTotal) + ' MB')

    def handleFix(self):
        SysHelper.fix_netsh()
        restart_msg = "To fix network, you need to restart the computer. Restart now?"
        reply = QMessageBox.question(self, 'Warning', restart_msg, QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            SysHelper.restart_pc()

    def handleClearTraffic(self):
        self.mainControl.clear_traffic()

    def handleViewMainPage(self):
        QDesktopServices.openUrl(QUrl("http://%s" % MAIN_DOMAIN))

    # ==================== MainControl callbacks ====================

    def mainConnectCallback(self):
        self.connected = True
        self.tray.setToolTip(self.getTooltips())
        self.toggleConnectBtn.setText('Setting up tunnel...')

    def mainTuntapSetCallback(self):
        self.toggleConnectBtn.setText('Setting up tunnel controller...')

    def mainTapControlSetCallback(self):
        self.toggleConnectBtn.setText('Disconnect')
        self.toggleConnectBtn.setEnabled(True)

    def mainStopCallback(self):
        self.toggleConnectBtn.setText('Connect')
        self.toggleConnectBtn.setEnabled(True)
        self.addrEdit.setEnabled(True)
        self.portEdit.setEnabled(True)
        self.userEdit.setEnabled(True)
        self.secretEdit.setEnabled(True)
        self.running = False
        self.connected = False
        self.tray.setToolTip(self.getTooltips())

    # ==================== Override ====================

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.m_drag = True
            self.m_DragPosition = event.globalPos() - self.pos()
            event.accept()
            self.setCursor(QCursor(Qt.OpenHandCursor))

    def mouseMoveEvent(self, QMouseEvent):
        if Qt.LeftButton and self.m_drag:
            if not self.m_DragPosition:
                return
            self.move(QMouseEvent.globalPos() - self.m_DragPosition)
            QMouseEvent.accept()

    def mouseReleaseEvent(self, QMouseEvent):
        self.m_drag = False
        self.setCursor(QCursor(Qt.ArrowCursor))

    def closeEvent(self, event):
        self.tray.hide()


MAIN_WINDOW = None

if __name__ == '__main__':
    try:
        sys.stderr = open('error.log', 'w+')
        LOGGER.info("start app, version: %s" % VERSION_CODE)
        app = QApplication(sys.argv)

        # check privilige
        if not ctypes.windll.shell32.IsUserAnAdmin():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Please run as administrator!")
            msg.setWindowTitle("Error")
            sys.exit(msg.exec_())

        # check tap
        while not get_tap_iface():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("First time running requires an installation of TAP driver")
            msg.setWindowTitle("Info")
            msg.exec_()
            SysHelper.install_tap()
            time.sleep(1)

        MAIN_WINDOW = FrontWindow()
        sys.exit(app.exec_())
    except Exception as err:
        LOGGER.error(err)
        LOGGER.error(traceback.format_exc())
        exit(1)
