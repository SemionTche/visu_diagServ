#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 2023/07/01
@author: juliengautier & leopold Rousseau
window image
"""

from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt6.QtWidgets import QLabel, QMainWindow, QFileDialog,QStatusBar
from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtGui import QIcon, QShortcut
from PIL import Image
import sys
import time
import pyqtgraph as pg  # pyqtgraph biblio permettent l'affichage
import numpy as np
import qdarkstyle  # pip install qdakstyle https://github.com/ColinDuquesnoy/QDarkStyleSheet  sur conda
import os

import pathlib
from scipy.ndimage import median_filter
#from winCrop import WINCROP
from visu.WinCut import GRAPHCUT
from visu.winMeas import MEAS
from visu.InputElectrons import InputE
from visu.CalculTraj import WINTRAJECTOIRE
import Deconvolve_Spectrum as Deconvolve

sys.path.insert(1, 'spectrum_analysis')
sepa = os.sep

class WINSPECTRO(QMainWindow):
    signalMeas = QtCore.pyqtSignal(object)
    def __init__(self, parent=None, file=None, conf=None, name='VISU',**kwds):
        
        super().__init__()
        self.name = name
        self.parent = parent
        p = pathlib.Path(__file__)
        self.icon = str(p.parent) + sepa + 'icons' + sepa




        self.window_setup()

        # Create calibration for spectrum deconvolution _ LHC
        self.deconv_calib = str(p.parent) + sepa+'spectrum_analysis' + sepa
        self.calibration_data = Deconvolve.CalibrationData(cal_path=self.deconv_calib + 'dsdE_Small_LHC.txt')
        # Create initialization object for spectrum deconvolution _ LHC
        initImage = Deconvolve.spectrum_image(im_path=self.deconv_calib +
                                           'magnet0.4T_Soectrum_isat4.9cm_26bar_gdd25850_HeAr_0002.TIFF',
                                   revert=True)
        self.deconvolved_spectrum = Deconvolve.DeconvolvedSpectrum(initImage, self.calibration_data, 0.5,
                                                              20.408, 0.1,
                                                              "zero", (1953, 635))
        self.setup()

    def window_setup(self):

        self.isWinOpen = False
        self.setWindowTitle('Electrons spectrometer')
        self.setWindowIcon(QIcon(self.icon+'LOA.png'))
        self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
        self.setWindowIcon(QIcon('./icons/LOA.png'))
        self.setGeometry(100, 30, 800, 800)

        self.toolBar = self.addToolBar('tools')
        self.toolBar.setMovable(False)
        menubar = self.menuBar()
#        menubar.setNativeMenuBar(False)
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        self.fileMenu = menubar.addMenu('&File')

    def setup(self):

        self.vbox2 = QVBoxLayout()
        self.winImage = pg.GraphicsLayoutWidget()
        self.winImage.setContentsMargins(0, 0, 0, 0)
        self.winImage.setAspectLocked(False)

        self.winImage.ci.setContentsMargins(0, 0, 0, 0)
        self.vbox2.addWidget(self.winImage)
        self.vbox2.setContentsMargins(0, 0, 0, 0)
        
        self.p1 = self.winImage.addPlot()
        self.imh = pg.ImageItem()
        self.axeX = self.p1.getAxis('bottom')
        self.axeY = self.p1.getAxis('left')
        self.p1.addItem(self.imh)
        self.p1.setMouseEnabled(x=False, y=False)
        self.p1.setContentsMargins(20, 20, 20, 20)
    

        self.p1.showAxis('right', show=False)
        self.p1.showAxis('top', show=False)
        self.p1.showAxis('left', show=True)
    
        self.axeX = self.p1.getAxis('bottom')
        self.axeY = self.p1.getAxis('left')
        self.axeX.setLabel(' Energy (Mev) ')
        self.axeY.setLabel( ' mrad ')

        self.imh.setImage(self.deconvolved_spectrum.image.T, autoLevels=True, autoDownsample=True)
        self.imh.setRect(
            self.deconvolved_spectrum.energy[0],  # x origin
            self.deconvolved_spectrum.angle[0],  # y origin
            self.deconvolved_spectrum.energy[-1] - self.deconvolved_spectrum.energy[0],  # width
            self.deconvolved_spectrum.angle[-1] - self.deconvolved_spectrum.angle[0] ) # height

        self.winImage2 = pg.GraphicsLayoutWidget()
        self.winPLOT = self.winImage2.addPlot()
        self.vbox2.addWidget(self.winImage2)
        self.pCut = self.winPLOT.plot()
        self.winPLOT.setLabel('bottom', 'Energy (Mev)')
        self.winPLOT.showAxis('right', show=False)
        self.winPLOT.showAxis('top', show=False)
        self.winPLOT.showAxis('left', show=True)
        self.winPLOT.showAxis('bottom', show=True)
        self.axeX = self.winPLOT.getAxis('bottom')
        self.p1.setAxis=self.axeX

        MainWidget = QWidget()
        MainWidget.setLayout(self.vbox2)
        self.setCentralWidget(MainWidget)

        # histogramvalue()
        self.hist = pg.HistogramLUTItem()
        self.hist.setImageItem(self.imh)
        self.hist.autoHistogramRange()
        self.hist.gradient.loadPreset('flame')

        if self.parent is not None:
            # if signal emit in another thread (see visual)
            self.parent.signalSpectro.connect(self.Display)

    def checkBoxScaleImage(self):

        if self.checkBoxScale.isChecked():
            self.checkBoxScale.setIcon(QtGui.QIcon(self.icon+"expand.png"))
            self.checkBoxScale.setText('Auto Scale On')
        else:
            self.checkBoxScale.setIcon(QtGui.QIcon(self.icon+"minimize.png"))
            self.checkBoxScale.setText('Auto Scale Off')

    def Display(self, data):
        self.dataOrg = data
        self.deconvolved_spectrum.deconvolve_data(np.flip(data.T, axis=1))
        self.deconvolved_spectrum.integrate_spectrum((600, 670), (750, 850))
        self.imh.setImage(self.deconvolved_spectrum.image.T, autoLevels=True, autoDownsample=True)



    def SaveF(self):
        # save as tiff
        fname = QFileDialog.getSaveFileName(self, "Save data as TIFF", self.path)
        self.path = os.path.dirname(str(fname[0]))
        fichier = fname[0]
        print(fichier, ' is saved')
        self.conf.setValue(self.name+"/path", self.path)
        time.sleep(0.1)
        self.dataS = np.rot90(self.data, 1)
        img_PIL = Image.fromarray(self.dataS)
        img_PIL.save(str(fname[0])+'.TIFF', format='TIFF')
        

        
if __name__ == "__main__":
    appli = QApplication(sys.argv)
    appli.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
    file= str(pathlib.Path(__file__).parents[0])+'/tir_025.TIFF'
    e =WINSPECTRO(name='VISU', file=file)
    e.show()
    appli.exec_()
