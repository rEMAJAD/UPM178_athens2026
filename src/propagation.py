"""Small/medium urban Hata; coordinates km, heights m, frequency MHz."""
from dataclasses import dataclass, asdict
import numpy as np


@dataclass(frozen=True)
class Radio:
    frequency_mhz: float = 900.0
    mobile_height_m: float = 1.5
    tx_power_dbm: float = 43.0  # reference; actual choices come from settings.POWERS_DBM
    tx_gain_dbi: float = 15.0
    rx_gain_dbi: float = 0.0
    feeder_loss_db: float = 2.0
    sensitivity_dbm: float = -95.0
    margin_db: float = 10.0

    def __post_init__(self):
        if not all(np.isfinite(v) for v in asdict(self).values()):
            raise ValueError('Radio parameters must be finite')
        if not 150 <= self.frequency_mhz <= 1500 or not 1 <= self.mobile_height_m <= 10:
            raise ValueError('Outside classical Hata frequency/mobile-height range')
        if self.margin_db < 0 or self.feeder_loss_db < 0:
            raise ValueError('Loss and margin must be nonnegative')

    @property
    def threshold_dbm(self):
        return self.sensitivity_dbm + self.margin_db


def path_loss(distance_km, height_m, radio=Radio()):
    """Distances <1 km are clamped to 1 km, not accurate near-field predictions.

    Reject >20 km instead of silently extrapolating beyond empirical validity.
    """
    d, h = np.asarray(distance_km, dtype=float), np.asarray(height_m, dtype=float)
    if not np.all(np.isfinite(d)) or np.any((d < 0) | (d > 20)):
        raise ValueError('Distance must be finite and between 0 and 20 km')
    if not np.all(np.isfinite(h)) or np.any((h < 30) | (h > 200)):
        raise ValueError('BTS height must be between 30 and 200 m')
    lf, lh = np.log10(radio.frequency_mhz), np.log10(h)
    correction = (1.1 * lf - 0.7) * radio.mobile_height_m - (1.56 * lf - 0.8)
    return 69.55 + 26.16 * lf - 13.82 * lh - correction + (44.9 - 6.55 * lh) * np.log10(np.maximum(d, 1))


def received_power(distance_km, height_m, radio=Radio()):
    return radio.tx_power_dbm + radio.tx_gain_dbi + radio.rx_gain_dbi - radio.feeder_loss_db - path_loss(distance_km, height_m, radio)


def covered(power_dbm, radio=Radio()):
    return np.asarray(power_dbm) >= radio.threshold_dbm


def power_matrix(stations, heights, points, radio=Radio(), powers=None):
    d = np.linalg.norm(np.asarray(stations)[:, None, :] - np.asarray(points)[None, :, :], axis=2)
    powers = np.asarray([radio.tx_power_dbm] if powers is None else powers)
    if powers.ndim != 1 or len(powers) == 0 or not np.all(np.isfinite(powers)):
        raise ValueError('Provide finite transmitter power choices')
    base = received_power(d[:, None, :], np.asarray(heights)[None, :, None], radio)
    return base[:, :, None, :] + (powers - radio.tx_power_dbm)[None, None, :, None]


def deployment_power(stations, heights, points, selected, radio=Radio(), powers=None):
    """Best serving signal, not a sum of unrelated transmitters' powers."""
    best = np.full(len(points), -np.inf)
    powers = [radio.tx_power_dbm] if powers is None else powers
    for i, k, p in selected:
        distance = np.linalg.norm(np.asarray(points) - np.asarray(stations)[i], axis=1)
        signal = received_power(distance, heights[k], radio) + powers[p] - radio.tx_power_dbm
        best = np.maximum(best, signal)
    return best
