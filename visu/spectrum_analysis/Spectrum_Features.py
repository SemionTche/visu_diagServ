import numpy as np
import math as m

def weighted_avg_and_std(values: np.ndarray, weights: np.ndarray):
    average = np.average(values, weights=weights)
    # Fast and numerically precise:
    variance = np.average((values-average)**2, weights=weights)
    return (average, m.sqrt(variance))


def build_dict(energy: np.ndarray, data: np.ndarray, shotNum: int):
    mean_energy, std_energy = weighted_avg_and_std(energy, data)
    data_dict = {('Std energy', std_energy),
                 ('Mean energy', mean_energy),
                 ('Shot number', shotNum)}
    return data_dict