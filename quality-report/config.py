import math

infinity = math.inf

# Fixation detection (Savitzky-Golay)
SG_WINDOW_LENGTH = 50  # milliseconds
SG_DEGREE = 2

# Acceptable thresholds
ACCEPTABLE_NUM_CALIBRATIONS = [2, 5]
ACCEPTABLE_NUM_VALIDATION = (13,15)
ACCEPTABLE_AVG_VALIDATION_SCORES = (0.0, 0.6)
ACCEPTABLE_MAX_VALIDATION_SCORES = (0.0, 1.5)
ACCEPTABLE_VALIDATION_ERRORS = ["GOOD"]
ACCEPTABLE_DATA_LOSS_RATIOS = (0.0, 0.10)
ACCEPTABLE_RECORDING_DURATIONS = (600, 7_200)  # seconds
ACCEPTABLE_NUM_PRACTICE_TRIALS = 2
ACCEPTABLE_NUM_TRIALS = 10

EXPECTED_SAMPLING_RATE = 1000  # Hz


TRACKED_EYE = ["L", "R", "RIGHT", "LEFT"]