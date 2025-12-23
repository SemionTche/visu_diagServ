#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 2025/12/23
@author: Aline Vernier
Spectrum deconvolution + make data available
"""
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QHBoxLayout, QGridLayout
from PyQt6.QtWidgets import (QLabel, QMainWindow, QFileDialog, QStatusBar,
                             QCheckBox, QDoubleSpinBox, QSlider, QPushButton, QLineEdit)
from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtGui import QIcon, QShortcut, QFont
import sys
import pyqtgraph as pg
import numpy as np
import qdarkstyle
import os
import pathlib

from visu.spectrum_analysis import Deconvolve_Spectrum as Deconvolve
from visu.spectrum_analysis import Spectrum_Features
from visu.spectrum_analysis import Build_Interface

sys.path.insert(1, 'spectrum_analysis')
sepa = os.sep

class WINSPECTRO(Build_Interface.Spectrometer_Interface):
    signalSpectroDict = QtCore.pyqtSignal(object)

    def __init__(self, parent=None, file=None, conf=None, name='VISU', **kwds):
        '''
        class WINSPECTRO inherits interface from Build_Interface.Spectrometer_Interface
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
        #self.setup()
        self.action_button()

        # Load calibration data
        self.load_calib()
        self.graph_setup()
        self.signal_setup()


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
                                                                   offset=self.lanex_offset_mm_control.value())

    def graph_setup(self):

        self.spectrum_2D_image.setLabel('bottom', 'Energy (MeV)')
        self.spectrum_2D_image.setLabel('left', 'mrad ')

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
