import numpy as np
import math as m


def find_nearest(data, value):
    return (np.abs(data - value)).argmin()
def find_indices(energy: np.ndarray, data_counts: np.ndarray, energy_bounds: list = None):
    '''
    Extracts subdata from energy and data array, given energy bounds specified in interface
    :param energy:
    :return:
    '''
    if energy_bounds is None:
        return [0, -1]
    else:
        low_index= find_nearest(energy, energy_bounds[0])
        high_index= find_nearest(energy, energy_bounds[1])
        return low_index, high_index


def weighted_avg_and_std(energy: np.ndarray, data_counts: np.ndarray):
    average = np.average(energy, weights=data_counts)
    variance = np.average((energy - average) ** 2, weights=data_counts)
    return (average, m.sqrt(variance))


def build_dict(energy: np.ndarray, data: np.ndarray, shotNum: int, energy_bounds):
    low, high = find_indices(energy, data, energy_bounds)
    mean_energy, std_energy = weighted_avg_and_std(energy[low:high],data[low:high])
    data_dict = dict((('Std energy', std_energy),
                      ('Mean energy', mean_energy),
                      ('Shot number', shotNum)))
    return data_dict