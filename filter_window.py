import sys

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from config_helper import load_filter, save_filter

class FilterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.initFilter()

    def initUI(self):
        self.setFixedSize(350, 333)
        self.setWindowTitle('Outernet - Filter')
        self.setWindowIcon(QIcon('res/icon.png'))

        filterTypeLabel = QLabel('Filter type', self)
        filterTypeLabel.resize(112, 20)
        filterTypeLabel.setObjectName('NormalLabel')
        filterTypeLabel.move(20, 20)

        self.filterTypeCB = QComboBox(self)
        self.filterTypeCB.addItems(['Blacklist'])
        self.filterTypeCB.resize(120, 20)
        self.filterTypeCB.move(210, 20)

        filterDomainLabel = QLabel('Filter domains', self)
        filterDomainLabel.resize(112, 20)
        filterDomainLabel.setObjectName('NormalLabel')
        filterDomainLabel.move(20, 40)

        self.filterDomainEdit = QPlainTextEdit(self)
        self.filterDomainEdit.setPlaceholderText("www\\.baidu\\.com\nwww\\.google\\.com")
        self.filterDomainEdit.resize(310, 80)
        self.filterDomainEdit.move(20, 70)

        filterIPLabel = QLabel('Filter IPs', self)
        filterIPLabel.resize(112, 20)
        filterIPLabel.setObjectName('NormalLabel')
        filterIPLabel.move(20, 155)

        self.filterIPEdit = QPlainTextEdit(self)
        self.filterIPEdit.setPlaceholderText("8.8.8.8/32\n8.8.4.4/32")
        self.filterIPEdit.resize(310, 80)
        self.filterIPEdit.move(20, 185)

        self.saveBtn = QPushButton("Save", self)
        self.saveBtn.clicked.connect(self.onSaveBtnClicked)
        self.saveBtn.resize(150, 25)
        self.saveBtn.move(20, 280)

        self.saveBtn = QPushButton("Reset", self)
        self.saveBtn.clicked.connect(self.onResetBtnClicked)
        self.saveBtn.resize(150, 25)
        self.saveBtn.move(180, 280)

    def initFilter(self):
        ffilter = load_filter()

        if ffilter is None:
            return

        ftype = ffilter.get('type')
        domains = ffilter.get('domains')
        ips = ffilter.get('ips')

        index = self.filterTypeCB.findText(ftype, Qt.MatchFixedString)
        self.filterTypeCB.setCurrentIndex(index)
        self.filterDomainEdit.setPlainText(domains)
        self.filterIPEdit.setPlainText(ips)

    def onSaveBtnClicked(self):
        ffilter = {}
        ffilter['type'] = self.filterTypeCB.currentText()
        ffilter['domains'] = self.filterDomainEdit.toPlainText()
        ffilter['ips'] = self.filterIPEdit.toPlainText()

        save_filter(ffilter)

        QMessageBox.information(self, "info", "Filter will be enable on next connection!")

    def onResetBtnClicked(self):
        self.initFilter()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    test_window = FilterWindow()
    test_window.show()
    sys.exit(app.exec_())
