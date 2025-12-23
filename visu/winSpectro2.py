#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 2025/12/16
@author: Aline Vernier
Spectrum deconvolution + make data available
"""
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QHBoxLayout, QGridLayout
from PyQt6.QtWidgets import (QLabel, QMainWindow, QFileDialog,QStatusBar,
                             QCheckBox, QDoubleSpinBox, QSlider, QPushButton, QLineEdit)
from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtGui import QIcon, QShortcut, QFont
from PIL import Image
import sys
import time
import pyqtgraph as pg
import numpy as np
import qdarkstyle
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

        # Toggle design
        TogOff = self.icon+'Toggle_Off.png'
        TogOn = self.icon+'Toggle_On.png'
        TogOff = pathlib.Path(TogOff)
        TogOff = pathlib.PurePosixPath(TogOff)
        TogOn = pathlib.Path(TogOn)
        TogOn = pathlib.PurePosixPath(TogOn)
        self.setStyleSheet("QCheckBox::indicator{width: 30px;height: 30px;}"
                           "QCheckBox::indicator:unchecked { image : url(%s);}"
                           "QCheckBox::indicator:checked { image:  url(%s);}"
                           "QCheckBox{font :10pt;}" % (TogOff, TogOn))

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
        self.vbox2widget.setFixedWidth(350)
        self.hbox.addWidget(self.vbox2widget)

        # Title
        title_layout = QGridLayout()
        self.vbox2.addLayout(title_layout)
        Title = QLabel('Controls and indicators')
        Title.setFont(QFont('Arial', 14))
        ph_1 = QLabel()
        ph_2 = QLabel()
        title_layout.addWidget(ph_1, 0, 0)
        title_layout.addWidget(Title, 0, 1)
        title_layout.addWidget(ph_2, 0, 2)



        #####################################################################
        #       Fill layout with graphs, controls and indicators
        #####################################################################



        # 2D plot (image histogram) in LHS vbox
        self.winImage = pg.GraphicsLayoutWidget()
        self.vbox1.addWidget(self.winImage)

        # Add plot in column 0
        self.spectrum_2D_image = self.winImage.addPlot(row=0, col=0)
        self.image_histogram = pg.ImageItem()
        self.spectrum_2D_image.addItem(self.image_histogram)

        # Setup histogram LUT
        self.hist = pg.HistogramLUTItem()
        self.hist.setImageItem(self.image_histogram)
        self.hist.gradient.loadPreset('flame')

        # Hide the actual plot region
        self.hist.region.setVisible(False)  # Hides the draggable region
        self.hist.vb.setVisible(False)  # Hides the ViewBox containing histogram
        self.winImage.addItem(self.hist)

        # Setup 1D plot (dN/dE vs. E)
        self.graph_widget = pg.GraphicsLayoutWidget()
        self.vbox1.addWidget(self.graph_widget)

        self.dnde_image = self.graph_widget.addPlot()
        self.dnde_image.setContentsMargins(10, 10, 10, 10)

        # Controls and indicators, labels
        grid_layout_enable_controls = QGridLayout()
        lock_controls = QLabel('Lock controls')
        self.locked_unlocked = QLabel('Unlocked')
        self.enable_controls = QCheckBox()
        self.enable_controls.setChecked(True)
        grid_layout_enable_controls.addWidget(lock_controls, 0, 0)
        grid_layout_enable_controls.addWidget(self.enable_controls, 0, 1)
        grid_layout_enable_controls.addWidget(self.locked_unlocked, 0, 2)
        self.vbox2.addLayout(grid_layout_enable_controls)

        grid_layout_config = QGridLayout()
        self.config_path_button = QPushButton('Path : ')
        self.config_path_button.setFixedWidth(50)
        self.config_path_box = QLineEdit('spectrum analysis')
        self.config_path_box.setMaximumHeight(60)
        grid_layout_config.addWidget(self.config_path_button, 0, 0)
        grid_layout_config.addWidget(self.config_path_box, 0, 1)
        self.vbox2.addLayout(grid_layout_config)

        self.flip_image = QCheckBox('Deflect.: R to L?', self)
        self.flip_image.setChecked(True)

        lanex_offset_label = QLabel('Lanex Offset (+ to low E)')
        self.lanex_offset_mm_control = QDoubleSpinBox()
        self.lanex_offset_mm_control.setValue(0)
        self.lanex_offset_mm_control.setSingleStep(.1)
        self.lanex_offset_mm_control.setMinimum(-100.)
        self.lanex_offset_mm = self.lanex_offset_mm_control.value()

        cutoff_energies_label = QLabel('Cutoff energies (MeV)')
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
        self.grid_layout = QGridLayout()
        self.vbox2.addLayout(self.grid_layout)  # add grid to RHS panel
        self.vbox2.addStretch(1)
        self.grid_layout.addWidget(QLabel(), 1, 2)
        self.grid_layout.addWidget(self.flip_image, 2, 0)
        self.grid_layout.addWidget(cutoff_energies_label, 3, 0)
        self.grid_layout.addWidget(self.min_cutoff_energy_control, 3, 2)
        self.grid_layout.addWidget(self.max_cutoff_energy_control, 3, 3)
        self.grid_layout.addWidget(lanex_offset_label, 4, 0)
        self.grid_layout.addWidget(self.lanex_offset_mm_control, 4, 3)


    #####################################################################
    #                       Interface actions
    #####################################################################

    def action_button(self)->None:
        self.min_cutoff_energy_control.valueChanged.connect(self.change_energy_bounds)
        self.max_cutoff_energy_control.valueChanged.connect(self.change_energy_bounds)
        self.lanex_offset_mm_control.valueChanged.connect(self.change_lanex_offset_mm)
        self.enable_controls.stateChanged.connect(self.enable_disable_controls)


    def enable_disable_controls(self):
        '''
        Enable or disable elements on interface
        :return:
        '''
        if self.enable_controls.isChecked():
            self.locked_unlocked.setText('Unlocked')
        else:
            self.locked_unlocked.setText('Locked')
        self.min_cutoff_energy_control.setEnabled(self.enable_controls.isChecked())
        self.max_cutoff_energy_control.setEnabled(self.enable_controls.isChecked())
        self.flip_image.setEnabled(self.enable_controls.isChecked())
        self.lanex_offset_mm_control.setEnabled(self.enable_controls.isChecked())
        self.config_path_button.setEnabled(self.enable_controls.isChecked())
        self.config_path_box.setEnabled(self.enable_controls.isChecked())

    def change_energy_bounds(self)->None:
        '''
        Change energy bouds for spectrum statistics and integration
        :return: None
        '''
        self.min_cutoff_energy = self.min_cutoff_energy_control.value()
        self.max_cutoff_energy = self.max_cutoff_energy_control.value()

    def change_lanex_offset_mm(self)->None:
        '''
        Change offset with respect to zero or reference point (manual offset or motorized)
        :return: None
        '''
        self.lanex_offset_mm = self.lanex_offset_mm_control.value()
        self.dnde_image.clear()
        self.load_calib()
        self.graph_setup()


    #####################################################################
    #                  Setup calibration for deconvolution
    #####################################################################

    def load_calib(self):
        # Load calibration for spectrum deconvolution
        p = pathlib.Path(__file__)
        self.deconv_calib = str(p.parent) + sepa + 'spectrum_analysis' + sepa
        self.calibration_data = Deconvolve.CalibrationData(cal_path=self.deconv_calib + 'dsdE_default.txt')
        self.calibration_data_json = None
        # Create initialization object for spectrum deconvolution
        initImage = Deconvolve.spectrum_image(im_path=self.deconv_calib +
                                                      'magnet0.4T_Soectrum_isat4.9cm_26bar_gdd25850_HeAr_0002.TIFF',
                                              revert=True)
        self.deconvolved_spectrum = Deconvolve.DeconvolvedSpectrum(initImage, self.calibration_data,
                                                                   0.5, 20.408, 0.1,
                                                                   "zero", (1953, 635),
                                                                   4.33e-6,
                                                                   offset= self.lanex_offset_mm_control.value())

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



    #####################################################################
    #                       Setup DiagServ signal
    #####################################################################

    def signal_setup(self):

        if self.parent is not None:
            # if signal emit in another thread (see visual)
            self.parent.signalSpectro.connect(self.Display)
            self.parent.signalSpectroList.connect(self.spectro_dict)

    #####################################################################
    #       Display and generate data for DiagServ (dictionary)
    #####################################################################
    def Display(self, data):

        # Deconvolve and display 2D data
        if self.flip_image.isChecked():
            self.deconvolved_spectrum.deconvolve_data(np.flip(data.T, axis=1))
        else:
            self.deconvolved_spectrum.deconvolve_data(data.T)
        self.image_histogram.setImage(self.deconvolved_spectrum.image.T, autoLevels=True, autoDownsample=True)

        # Integrate over angle and show graph
        self.deconvolved_spectrum.integrate_spectrum((600, 670), (750, 850))
        #self.update_image_levels()
        self.dnde_image.plot(self.deconvolved_spectrum.energy, self.deconvolved_spectrum.integrated_spectrum)

    def spectro_dict(self, temp_dataArray):
        # Creation of dictionary to pass to diagServ ; cut energy from interface to remove noise
        self.spectro_data_dict = Spectrum_Features.build_dict(self.deconvolved_spectrum.energy,
                                                              self.deconvolved_spectrum.integrated_spectrum,
                                                              temp_dataArray[1],
                                                              energy_bounds=[self.min_cutoff_energy, self.max_cutoff_energy])
        self.signalSpectroDict.emit(self.spectro_data_dict) # Signal for DiagServ


if __name__ == "__main__":

    appli = QApplication(sys.argv)
    appli.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
    file= str(pathlib.Path(__file__).parents[0])+'/tir_025.TIFF'
    e =WINSPECTRO(name='VISU', file=file)
    e.show()
    appli.exec_()
