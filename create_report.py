""" creating a report based on the metadata of the asc experiment file. It includes quality mesuremntes based on threshold, specified in a config file """

import argparse
import configparser

import pymovements as pm

from_asc = pm.gaze.io.from_asc


def create_config(path):
    config = configparser.ConfigParser()

    # Add sections and key-value pairs
    config['General'] = {'debug': True, 'log_level': 'info'}
    config['Database'] = {'db_name': 'example_db',
                          'db_host': 'localhost', 'db_port': '5432'}

    config['validation'] = {'validation_score_avg': 0.3, 'validation_score_max': 0.7}
    config['trial_duration'] = {'start_timestamp': 897432.0, 'stop_timestamp': 897543.0, 'duration_ms': 111.0,
                                'num_samples': 225}

    # Write the configuration to a file
    with open(path, 'w') as configfile:
        config.write(configfile)


def read_config(path):
    # Create a ConfigParser object
    config = configparser.ConfigParser()

    # Read the configuration file
    config.read(path)

    # Access values from the configuration file
    debug_mode = config.getboolean('General', 'debug')
    log_level = config.get('General', 'log_level')
    db_name = config.get('Database', 'db_name')
    db_host = config.get('Database', 'db_host')
    db_port = config.get('Database', 'db_port')

    # Return a dictionary with the retrieved values
    config_values = {
        'debug_mode': debug_mode,
        'log_level': log_level,
        'db_name': db_name,
        'db_host': db_host,
        'db_port': db_port
    }

    return config_values


def create_report(file, config):
    _, metadata = from_asc(file)


def parse_args():
    parser = argparse.ArgumentParser(description='create a quality check report of an asc experiment file')
    parser.add_argument(
        '--file_path',
        type=str,
        default='output/ch1hr007.asc',
        help='Path to the file containing asc_file'
    )

    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config.yaml',
        help='Path to the config file, containing the quality thresholds for the report.'
    )

    parser.add_argument(
        '--save-report', '-s',
        type=str,
        help='Save the report to a txt file at specified path',
        default='report.txt',
    )

    return parser.parse_args()


def main():
    args = parse_args()
    create_report(args.file_path, args.config)


if __name__ == "__main__":
    # load the data
    config_file_path = 'config.ini'
    filepath = "output/ch1hr007.asc"
    create_config(config_file_path)
    # create_report(filepath, config)
