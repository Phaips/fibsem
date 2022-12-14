# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'detection_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(1016, 692)
        self.frame_main = QtWidgets.QFrame(Dialog)
        self.frame_main.setGeometry(QtCore.QRect(0, 10, 994, 658))
        self.frame_main.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_main.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_main.setObjectName("frame_main")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.frame_main)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.frame_image = QtWidgets.QFrame(self.frame_main)
        self.frame_image.setMaximumSize(QtCore.QSize(1536, 1024))
        self.frame_image.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_image.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_image.setObjectName("frame_image")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.frame_image)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.label_image = QtWidgets.QLabel(self.frame_image)
        self.label_image.setText("")
        self.label_image.setObjectName("label_image")
        self.gridLayout_3.addWidget(self.label_image, 0, 0, 1, 1)
        self.gridLayout_2.addWidget(self.frame_image, 1, 1, 2, 1)
        self.frame_parameters = QtWidgets.QFrame(self.frame_main)
        self.frame_parameters.setMaximumSize(QtCore.QSize(200, 16777215))
        self.frame_parameters.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_parameters.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_parameters.setObjectName("frame_parameters")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.frame_parameters)
        self.gridLayout_4.setVerticalSpacing(6)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.label_header_2 = QtWidgets.QLabel(self.frame_parameters)
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_header_2.setFont(font)
        self.label_header_2.setObjectName("label_header_2")
        self.gridLayout_4.addWidget(self.label_header_2, 1, 1, 1, 1)
        self.comboBox_detection_type = QtWidgets.QComboBox(self.frame_parameters)
        self.comboBox_detection_type.setObjectName("comboBox_detection_type")
        self.gridLayout_4.addWidget(self.comboBox_detection_type, 2, 1, 1, 2)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_4.addItem(spacerItem, 15, 1, 1, 2)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Maximum)
        self.gridLayout_4.addItem(spacerItem1, 19, 1, 1, 2)
        self.label_movement = QtWidgets.QLabel(self.frame_parameters)
        self.label_movement.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_movement.setObjectName("label_movement")
        self.gridLayout_4.addWidget(self.label_movement, 17, 1, 1, 2)
        self.pushButton_continue = QtWidgets.QPushButton(self.frame_parameters)
        self.pushButton_continue.setMinimumSize(QtCore.QSize(0, 40))
        self.pushButton_continue.setObjectName("pushButton_continue")
        self.gridLayout_4.addWidget(self.pushButton_continue, 20, 1, 1, 2)
        self.label_movement_header = QtWidgets.QLabel(self.frame_parameters)
        self.label_movement_header.setTextFormat(QtCore.Qt.AutoText)
        self.label_movement_header.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_movement_header.setObjectName("label_movement_header")
        self.gridLayout_4.addWidget(self.label_movement_header, 16, 1, 1, 1)
        self.gridLayout_2.addWidget(self.frame_parameters, 1, 0, 2, 1)
        self.label_title = QtWidgets.QLabel(self.frame_main)
        self.label_title.setMaximumSize(QtCore.QSize(16777215, 50))
        font = QtGui.QFont()
        font.setPointSize(26)
        font.setBold(True)
        font.setWeight(75)
        self.label_title.setFont(font)
        self.label_title.setTextFormat(QtCore.Qt.PlainText)
        self.label_title.setObjectName("label_title")
        self.gridLayout_2.addWidget(self.label_title, 0, 0, 1, 2)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.label_header_2.setText(_translate("Dialog", "Detection Type"))
        self.label_movement.setText(_translate("Dialog", "TextLabel"))
        self.pushButton_continue.setText(_translate("Dialog", "Continue"))
        self.label_movement_header.setText(_translate("Dialog", "TextLabel"))
        self.label_title.setText(_translate("Dialog", "AutoLiftout Detection"))

