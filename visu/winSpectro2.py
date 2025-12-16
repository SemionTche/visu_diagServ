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

        self.setup()

        # Create calibration for spectrum deconvolution
        self.deconv_calib = str(p.parent) + sepa+'spectrum_analysis' + sepa
        self.calibration_data = Deconvolve.CalibrationData(cal_path=self.deconv_calib + 'dsdE_Small_LHC.txt')
        # Create initialization object for spectrum deconvolution
        initImage = Deconvolve.spectrum_image(im_path=self.deconv_calib +
                                           'magnet0.4T_Soectrum_isat4.9cm_26bar_gdd25850_HeAr_0002.TIFF',
                                   revert=True)
        self.deconvolved_spectrum = Deconvolve.DeconvolvedSpectrum(initImage, self.calibration_data, 0.5,
                                                              20.408, 0.1,
                                                              "zero", (1953, 635))
        self.graph_setup()


    def setup(self):
        self.isWinOpen = False
        self.setWindowTitle('Electrons spectrometer')
        self.setWindowIcon(QIcon(self.icon + 'LOA.png'))
        self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
        self.setWindowIcon(QIcon('./icons/LOA.png'))
        self.setGeometry(100, 30, 800, 800)

        self.toolBar = self.addToolBar('tools')
        self.toolBar.setMovable(False)
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        self.fileMenu = self.menuBar().addMenu('&File')

        self.vbox = QVBoxLayout()
        self.winImage = pg.GraphicsLayoutWidget()
        self.winImage.setAspectLocked(False)
        self.vbox.addWidget(self.winImage)

        self.spectrum_2D_image = self.winImage.addPlot()
        self.imh = pg.ImageItem()

    def graph_setup(self):

        self.axeX, self.axeY = (self.spectrum_2D_image.getAxis('bottom'),
                                self.spectrum_2D_image.getAxis('left'))
        self.spectrum_2D_image.addItem(self.imh)
        self.spectrum_2D_image.setContentsMargins(10, 10, 10, 10)

        self.axeX.setLabel(' Energy (MeV) ')
        self.axeY.setLabel( 'mrad ')

        self.imh.setImage(self.deconvolved_spectrum.image.T, autoLevels=True, autoDownsample=True)
        self.imh.setRect(
            self.deconvolved_spectrum.energy[0],  # x origin
            self.deconvolved_spectrum.angle[0],  # y origin
            self.deconvolved_spectrum.energy[-1] - self.deconvolved_spectrum.energy[0],  # width
            self.deconvolved_spectrum.angle[-1] - self.deconvolved_spectrum.angle[0] ) # height

        self.winImage2 = pg.GraphicsLayoutWidget()
        self.dnde_image = self.winImage2.addPlot()
        self.vbox.addWidget(self.winImage2)
        self.dnde_image.setLabel('bottom', 'Energy')
        self.dnde_image.setLabel('left', 'dN/dE (pC/MeV)')
        self.dnde_image.setContentsMargins(10, 10, 10, 10)

        MainWidget = QWidget()
        MainWidget.setLayout(self.vbox)
        self.setCentralWidget(MainWidget)

        # histogramvalue()
        self.hist = pg.HistogramLUTItem()
        self.hist.setImageItem(self.imh)
        self.hist.autoHistogramRange()
        self.hist.gradient.loadPreset('flame')

        if self.parent is not None:
            # if signal emit in another thread (see visual)
            self.parent.signalSpectro.connect(self.Display)

    def Display(self, data):

        # Deconvolve and display 2D data
        self.deconvolved_spectrum.deconvolve_data(np.flip(data.T, axis=1))
        self.imh.setImage(self.deconvolved_spectrum.image.T, autoLevels=True, autoDownsample=True)

        # Integrate over angle and show graph
        self.deconvolved_spectrum.integrate_spectrum((600, 670), (750, 850))
        self.dnde_image.plot(self.deconvolved_spectrum.energy, self.deconvolved_spectrum.integrated_spectrum)

        
if __name__ == "__main__":
    appli = QApplication(sys.argv)
    appli.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
    file= str(pathlib.Path(__file__).parents[0])+'/tir_025.TIFF'
    e =WINSPECTRO(name='VISU', file=file)
    e.show()
    appli.exec_()
