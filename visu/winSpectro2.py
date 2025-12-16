#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 2025/12/16
@author: Aline Vernier
Spectrum deconvolution + make data available
"""
import Spectrum_Features
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt6.QtWidgets import QLabel, QMainWindow, QFileDialog,QStatusBar
from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtGui import QIcon, QShortcut
from PIL import Image
import sys
import time
import pyqtgraph as pg  # pyqtgraph
import numpy as np
import qdarkstyle  # pip install qdarkstyle
import os
from scipy.signal import lfilter
import pathlib


import Deconvolve_Spectrum as Deconvolve
import Spectrum_Features as compute

sys.path.insert(1, 'spectrum_analysis')
sepa = os.sep

class WINSPECTRO(QMainWindow):
    signalMeas = QtCore.pyqtSignal(object)
    def __init__(self, parent=None, file=None, conf=None, name='VISU',**kwds):
        '''

        :param parent:
        :param file:
        :param conf:
        :param name:
        :param kwds:
        '''
        
        super().__init__()
        self.name = name
        self.parent = parent
        p = pathlib.Path(__file__)
        self.icon = str(p.parent) + sepa + 'icons' + sepa
        self.data_dict = {}

        # Main window setup
        self.setup()

        # Load calibration data
        self.load_calib()
        self.graph_setup()
        self.signal_setup()

    def setup(self):

        # Window setup
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

        # Setup vertical box with stacked graphs
        self.vbox = QVBoxLayout()
        MainWidget = QWidget()
        MainWidget.setLayout(self.vbox)
        self.setCentralWidget(MainWidget)

        # Setup 2D plot (image histogram)
        self.winImage = pg.GraphicsLayoutWidget()
        self.vbox.addWidget(self.winImage)

        self.spectrum_2D_image = self.winImage.addPlot()
        self.image_histogram = pg.ImageItem()
        self.spectrum_2D_image.addItem(self.image_histogram)
        self.spectrum_2D_image.setContentsMargins(10, 10, 10, 10)

        # histogramvalue()
        self.hist = pg.HistogramLUTItem()
        self.hist.setImageItem(self.image_histogram)
        self.hist.autoHistogramRange()
        self.hist.gradient.loadPreset('flame')

        # Setup 1D plot (dN/dE vs. E)
        self.graph_widget = pg.GraphicsLayoutWidget()
        self.vbox.addWidget(self.graph_widget)

        self.dnde_image = self.graph_widget.addPlot()
        self.dnde_image.setContentsMargins(10, 10, 10, 10)


    def load_calib(self):
        # Load calibration for spectrum deconvolution
        p = pathlib.Path(__file__)
        self.deconv_calib = str(p.parent) + sepa + 'spectrum_analysis' + sepa
        self.calibration_data = Deconvolve.CalibrationData(cal_path=self.deconv_calib + 'dsdE_Small_LHC.txt')
        # Create initialization object for spectrum deconvolution
        initImage = Deconvolve.spectrum_image(im_path=self.deconv_calib +
                                                      'magnet0.4T_Soectrum_isat4.9cm_26bar_gdd25850_HeAr_0002.TIFF',
                                              revert=True)
        self.deconvolved_spectrum = Deconvolve.DeconvolvedSpectrum(initImage, self.calibration_data,
                                                                   0.5, 20.408,
                                                                   0.1, "zero",
                                                                   (1953, 635), 4.33e-6)

    def graph_setup(self):

        self.spectrum_2D_image.setLabel('bottom', 'Energy (MeV)')
        self.spectrum_2D_image.setLabel( 'left', 'mrad ')

        self.image_histogram.setImage(self.deconvolved_spectrum.image.T, autoLevels=True, autoDownsample=True)
        self.image_histogram.setRect(
            self.deconvolved_spectrum.energy[0],  # x origin
            self.deconvolved_spectrum.angle[0],  # y origin
            self.deconvolved_spectrum.energy[-1] - self.deconvolved_spectrum.energy[0],  # width
            self.deconvolved_spectrum.angle[-1] - self.deconvolved_spectrum.angle[0] ) # height

        self.dnde_image.setLabel('bottom', 'Energy')
        self.dnde_image.setLabel('left', 'dN/dE (pC/MeV)')


    def signal_setup(self):

        if self.parent is not None:
            # if signal emit in another thread (see visual)
            self.parent.signalSpectro.connect(self.Display)

    def Display(self, data):

        # Deconvolve and display 2D data
        self.deconvolved_spectrum.deconvolve_data(np.flip(data.T, axis=1))
        self.image_histogram.setImage(self.deconvolved_spectrum.image.T, autoLevels=True, autoDownsample=True)

        # Integrate over angle and show graph
        self.deconvolved_spectrum.integrate_spectrum((600, 670), (750, 850))
        self.dnde_image.plot(self.deconvolved_spectrum.energy, self.deconvolved_spectrum.integrated_spectrum)

        # Creation of dictionary to pass to diagServ ; to be integrated to another function, with another signal
        # Only process data without noise! Maybe make function that automatically removes noise?
        self.data_dict = Spectrum_Features.build_dict(self.deconvolved_spectrum.energy[50:150],
                                                      self.deconvolved_spectrum.integrated_spectrum[50:150])
        print(self.data_dict)


if __name__ == "__main__":

    appli = QApplication(sys.argv)
    appli.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
    file= str(pathlib.Path(__file__).parents[0])+'/tir_025.TIFF'
    e =WINSPECTRO(name='VISU', file=file)
    e.show()
    appli.exec_()
