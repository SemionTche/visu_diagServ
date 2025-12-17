#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 2025/12/16
@author: Aline Vernier
Spectrum deconvolution + make data available
"""
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QHBoxLayout, QGridLayout
from PyQt6.QtWidgets import QLabel, QMainWindow, QFileDialog,QStatusBar, QCheckBox, QDoubleSpinBox, QSlider
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

from visu.spectrum_analysis import Deconvolve_Spectrum as Deconvolve
from visu.spectrum_analysis import Spectrum_Features

sys.path.insert(1, 'spectrum_analysis')
sepa = os.sep

class WINSPECTRO(QMainWindow):
    signalSpectroDict = QtCore.pyqtSignal(object)

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
        self.action_button()

        # Load calibration data
        self.load_calib()
        self.graph_setup()
        self.signal_setup()

    def setup(self):

        #####################################################################
        #                   Window setup
        #####################################################################
        self.isWinOpen = False
        self.setWindowTitle('Electrons spectrometer')
        self.setWindowIcon(QIcon(self.icon + 'LOA.png'))
        self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
        self.setWindowIcon(QIcon('./icons/LOA.png'))
        self.setGeometry(100, 30, 1200, 800)

        self.toolBar = self.addToolBar('tools')
        self.toolBar.setMovable(False)
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        self.fileMenu = self.menuBar().addMenu('&File')

        #####################################################################
        #                   Global layout and geometry
        #####################################################################

        # Horizontal box with LHS graphs, and RHS controls and indicators
        self.hbox = QHBoxLayout()
        MainWidget = QWidget()
        MainWidget.setLayout(self.hbox)
        self.setCentralWidget(MainWidget)

        # LHS vertical box with stacked graphs
        self.vbox1 = QVBoxLayout()
        self.hbox.addLayout(self.vbox1)

        # RHS vertical box with controls and indicators
        self.vbox2 = QVBoxLayout()
        self.vbox2widget = QWidget()
        self.vbox2widget.setLayout(self.vbox2)
        self.vbox2widget.setFixedWidth(300)
        self.hbox.addWidget(self.vbox2widget)

        # Title
        title_layout = QGridLayout()
        self.vbox2.addLayout(title_layout)
        Title = QLabel('Controls and indicators')
        ph_1 = QLabel()
        ph_2 = QLabel()
        title_layout.addWidget(ph_1, 0, 0)
        title_layout.addWidget(Title, 0, 1)
        title_layout.addWidget(ph_2, 0, 2)

        # Grid layout for controls and indicators
        self.grid_layout = QGridLayout()

        self.vbox2.addLayout(self.grid_layout)  # add grid to RHS panel
        self.vbox2.addStretch(1)

        #####################################################################
        #       Fill layout with graphs, controls and indicators
        #####################################################################

        # 2D plot (image histogram) in LHS vbox
        self.winImage = pg.GraphicsLayoutWidget()
        self.vbox1.addWidget(self.winImage)

        self.spectrum_2D_image = self.winImage.addPlot()
        self.image_histogram = pg.ImageItem()
        self.spectrum_2D_image.addItem(self.image_histogram)
        self.spectrum_2D_image.setContentsMargins(10, 10, 10, 10)

        # Setup colours in 2D plot
        self.hist = pg.HistogramLUTItem()
        self.hist.setImageItem(self.image_histogram)
        self.hist.autoHistogramRange()
        self.hist.gradient.loadPreset('flame')

        # Setup 1D plot (dN/dE vs. E)
        self.graph_widget = pg.GraphicsLayoutWidget()
        self.vbox1.addWidget(self.graph_widget)

        self.dnde_image = self.graph_widget.addPlot()
        self.dnde_image.setContentsMargins(10, 10, 10, 10)

        # Controls and indicators, labels

        self.flip_image = QCheckBox('Deflect.: R to L?', self)
        self.flip_image.setChecked(True)

        cutoff_energies = QLabel('Cutoff energies (MeV)')
        self.min_cutoff_energy_control = QDoubleSpinBox()  # for the value
        self.min_cutoff_energy_control.setValue(10)
        self.min_cutoff_energy = self.min_cutoff_energy_control.value()
        self.min_cutoff_energy_control.setMinimum(0)
        self.min_cutoff_energy_control.setSingleStep(1)

        self.max_cutoff_energy_control = QDoubleSpinBox()  # for the value
        self.max_cutoff_energy_control.setValue(200)
        self.max_cutoff_energy = self.max_cutoff_energy_control.value()
        self.max_cutoff_energy_control.setMinimum(50)
        self.max_cutoff_energy_control.setSingleStep(10)

        # Fill grid with controls and indicators

        self.grid_layout.addWidget(QLabel(), 1, 3)
        self.grid_layout.addWidget(self.flip_image, 2, 0)
        self.grid_layout.addWidget(cutoff_energies, 3, 0)
        self.grid_layout.addWidget(self.min_cutoff_energy_control, 3, 1)
        self.grid_layout.addWidget(self.max_cutoff_energy_control, 3, 2)

        # Brightness
        grid_layout_brightness = QGridLayout()
        grid_layout_brightness.addWidget(QLabel(), 0, 0)  # skip a line
        brightnessLabel = QLabel("Brightness:")
        grid_layout_brightness.addWidget(brightnessLabel, 1, 0)
        self.brightnessSlider = QSlider(Qt.Orientation.Horizontal)
        self.brightnessSlider.setRange(0, 100)
        self.brightnessSlider.setValue(50)
        grid_layout_brightness.addWidget(self.brightnessSlider, 2, 0)
        self.brightnessBox = QDoubleSpinBox()
        self.brightnessBox.setRange(0, 100)
        self.brightnessBox.setValue(self.brightnessSlider.value())
        grid_layout_brightness.addWidget(self.brightnessBox, 2, 1)
        self.vbox2.addLayout(grid_layout_brightness)

    #####################################################################
    #                       Interface actions
    #####################################################################

    def action_button(self):
        self.brightnessSlider.valueChanged.connect(self.updateBrightness)
        self.brightnessBox.valueChanged.connect(self.updateBrightnessBox)
        self.min_cutoff_energy_control.valueChanged.connect(self.change_energy_bounds)
        self.max_cutoff_energy_control.valueChanged.connect(self.change_energy_bounds)

    def change_energy_bounds(self):
        self.min_cutoff_energy = self.min_cutoff_energy_control.value()
        self.max_cutoff_energy = self.max_cutoff_energy_control.value()

    def updateBrightness(self, val):
        self.brightnessBox.setValue(self.brightnessSlider.value())
        # brightness levels
        levels = self.image_histogram.getLevels()
        if levels[0] is None:
            self.base_xmin = float(self.data.min())
            self.base_xmax = float(self.data.max())
        else:
            self.base_xmin = float(levels[0])
            self.base_xmax = float(levels[1])
        xmin = self.base_xmin

        span = self.base_xmax - self.base_xmin
        factor = (val - 50) / 50.0
        xmax = self.base_xmax - factor * span

        if xmax <= xmin:
            xmax = xmin + 1e-9

        self.image_histogram.setLevels([xmin, xmax])
        self.hist.setHistogramRange(xmin, xmax)

    def updateBrightnessBox(self):
        self.brightnessSlider.setValue(int(self.brightnessBox.value()))
        self.updateBrightness(self.brightnessBox.value())

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
            self.parent.signalSpectroList.connect(self.spectro_dict)

    def Display(self, data):

        # Deconvolve and display 2D data
        self.deconvolved_spectrum.deconvolve_data(np.flip(data.T, axis=1))
        self.image_histogram.setImage(self.deconvolved_spectrum.image.T, autoLevels=True, autoDownsample=True)

        # Integrate over angle and show graph
        self.deconvolved_spectrum.integrate_spectrum((600, 670), (750, 850))
        self.dnde_image.plot(self.deconvolved_spectrum.energy, self.deconvolved_spectrum.integrated_spectrum)
        self.updateBrightness(self.brightnessBox.value())

    def spectro_dict(self, temp_dataArray):
        # Creation of dictionary to pass to diagServ ; to be integrated to another function, with another signal
        # temp_dataArray : [data from parent, shot number] ; added data from parent in case we want to compute but
        # not display!
        # Only process data without noise! Maybe make function that automatically removes noise?
        self.spectro_data_dict = Spectrum_Features.build_dict(self.deconvolved_spectrum.energy,
                                                              self.deconvolved_spectrum.integrated_spectrum,
                                                              temp_dataArray[1], energy_bounds=[15, 100])
        self.signalSpectroDict.emit(self.spectro_data_dict)


if __name__ == "__main__":

    appli = QApplication(sys.argv)
    appli.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
    file= str(pathlib.Path(__file__).parents[0])+'/tir_025.TIFF'
    e =WINSPECTRO(name='VISU', file=file)
    e.show()
    appli.exec_()
