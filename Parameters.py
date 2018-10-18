"""
Module for parameter container and associated methods
#author: Daniel Polasky
#date: 10/16/2018
"""
import numpy as np
from decimal import Decimal


class MethodParams(object):
    """
    Container for all parameters associated with a method
    """
    def __init__(self, params_dict):
        self.combine_all_bool = None
        self.msms_bool = None
        self.cal_file = None
        self.optic_mode = None
        self.tune_file = None
        self.output_dir = None
        self.save_to_masslynx = None
        self.masslynx_dir = None
        self.functions_per_file = None
        self.save_dt = None
        self.delay_time_init = None
        self.date = None
        self.mz = None
        self.sample_name = None
        self.cv_step = None
        self.cv_start = None
        self.cv_end = None
        self.ms_start = None
        self.ms_end = None
        self.collect_time = None
        self.scan_time = None
        self.base_file_path = None

        self.params_dict = {}
        self.set_params(params_dict)


    def set_params(self, params_dict):
        """
        Set a series of parameters given a dictionary of (parameter name, value) pairs
        :param params_dict: Dictionary, key=param name, value=param value
        :return: void
        """
        for name, value in params_dict.items():
            try:
                # only set the attribute if it is present in the object - otherwise, raise attribute error
                self.__getattribute__(name)
                self.__setattr__(name, value)
            except AttributeError:
                # no such parameter
                print('No parameter name for param: ' + name)
                continue
        self.update_dict()

    def update_dict(self):
        """
        Build (or rebuild) a dictionary of all attributes contained in this object
        :return: void
        """
        for field in vars(self):
            value = self.__getattribute__(field)
            self.params_dict[field] = value


def parse_params_template_csv(params_file, descripts_file):
    """
    Parse a template CSV file containing one or several method editor runs. Generates a new
    MethodParams container for each analysis requested
    :param params_file: File to parse (.txt), headers = '#'
    :param descripts_file: Descriptions file with parameter descriptions and key names
    :return: list of param containers, combine all bool
    """
    col_locations, codenames, names, reqs, descripts = parse_param_descriptions(descripts_file)
    param_obj_list = []

    # initialize header information for later retrieval
    base_param_dict = {}

    # Read the template file
    done_with_headers = False
    with open(params_file, 'r') as parfile:
        for line in list(parfile):
            # check if we've reached the individual section yet
            if line.startswith('# INDIVIDUAL'):
                done_with_headers = True

            # skip headers and blank lines
            if line.startswith('#') or line.startswith('\n') or line.startswith(','):
                continue

            # read headers
            if not done_with_headers:
                splits = line.rstrip('\n').split(',')
                for index, split in enumerate(splits):
                    if split is not '':
                        key = col_locations[index + 20]     # +20 to distinguish header columns from lower columns
                        base_param_dict[key] = parse_value(split.strip())
            else:
                # read individual parameter lines and make a container for each
                current_param_dict = {}
                current_param_dict.update(base_param_dict)
                splits = line.rstrip('\n').split(',')
                for index, split in enumerate(splits):
                    if split is not '':
                        key = col_locations[index]
                        parsed_value = parse_value(split.strip())
                        current_param_dict[key] = parsed_value

                # initialize a parameter container
                param_obj_list.append(MethodParams(current_param_dict))

    return param_obj_list


def parse_value(value):
    """
    convert a string value into appropriate type
    :param value: string
    :return: various types
    """
    # Convert value from string to appropriate type
    if value == 'None':
        output_val = None
    else:
        # try parsing numbers
        try:
            try:
                if '_' in value:
                    # don't treat the date as an integer (pass it down to string)
                    raise ValueError
                output_val = int(value)
            except ValueError:
                if '_' in value:
                    raise ValueError
                float(value)    # test first with float because Decimal throws a weird error
                output_val = Decimal(value) # represent floats with Decimal, since exact values can be important for MassLynx
        except ValueError:
            # string value - try parsing booleans or leave as a string
            if value.lower() in ['true', 't', 'yes', 'y']:
                output_val = True
            elif value.lower() in ['false', 'f', 'no', 'n']:
                output_val = False
            else:
                output_val = value
    return output_val


def parse_params_file_oldtxt(params_file, descripts_file):
    """
    Parse a text file for all parameters. Returns a params_dict that can be used to
    set_params on a Parameters object
    :param params_file: File to parse (.txt), headers = '#'
    :param descripts_file: Descriptions file with parameter descriptions and key names
    :return: params_dict: Dictionary, key=param name, value=param value
    """
    col_locations, codenames, names, reqs, descripts = parse_param_descriptions(descripts_file)

    param_dict = {}
    try:
        with open(params_file, 'r') as pfile:
            lines = list(pfile)
            for line in lines:
                # skip headers and blank lines
                if line.startswith('#') or line.startswith('\n'):
                    continue
                splits = line.rstrip('\n').split('=')

                try:
                    key = codenames[splits[0].strip()]
                except KeyError:
                    print('Error: invalid parameter name: {}'.format(splits[0].strip()))
                    continue
                value = splits[1].strip()

                # catch 'None' values and convert to None
                if value == 'None':
                    param_dict[key] = None
                else:
                    # try parsing numbers
                    try:
                        try:
                            param_dict[key] = int(value)
                        except ValueError:
                            param_dict[key] = float(value)
                    except ValueError:
                        # string value - try parsing booleans or leave as a string
                        if value.lower() in ['true', 't', 'yes', 'y']:
                            param_dict[key] = True
                        elif value.lower() in ['false', 'f', 'no', 'n']:
                            param_dict[key] = False
                        else:
                            param_dict[key] = value
        return param_dict
    except FileNotFoundError:
        print('params file not found!')


def parse_param_descriptions(param_file):
    """
    Read in parameter descriptions and requirements from text (csv) file
    :param param_file: file to read (full system path)
    :return: dictionaries of 1) parameter display names, 2) parameter descriptions, 3) parameter
    requirements. All dicts will have keys corresponding to attributes of the Parameters object
    """
    names = {}
    descriptions = {}
    reqs = {}
    codenames = {}
    col_locations = {}

    with open(param_file) as p_file:
        lines = list(p_file)
        for line in lines:
            # skip header
            if line.startswith('#'):
                continue

            line = line.rstrip('\n')
            # parse a parameter name and description from the line
            splits = line.split(',')
            key = splits[0].strip()
            names[key] = splits[2].strip()
            descriptions[key] = splits[7].strip()
            codenames[splits[8].strip()] = key
            col_locations[int(splits[9].strip())] = key

            # parse parameter requirements
            param_type = splits[3].strip()
            if param_type == 'int':
                # parse lower and upper bounds
                if splits[4].strip() == 'ninf':
                    lower_bound = -np.inf
                else:
                    lower_bound = int(splits[4].strip())
                if splits[5].strip() == 'inf':
                    upper_bound = np.inf
                else:
                    upper_bound = int(splits[5].strip())
                reqs[key] = (param_type, [lower_bound, upper_bound])
            elif param_type == 'float':
                # parse lower and upper bounds
                if splits[4].strip() == 'ninf':
                    lower_bound = -np.inf
                else:
                    lower_bound = float(splits[4].strip())
                if splits[5].strip() == 'inf':
                    upper_bound = np.inf
                else:
                    upper_bound = float(splits[5].strip())
                reqs[key] = (param_type, [lower_bound, upper_bound])
            elif param_type == 'string' or param_type == 'bool':
                req_vals = [x.strip() for x in splits[6].strip().split(';')]
                # convert 'none' strings to actual Nonetype
                # for index, value in enumerate(req_vals):
                #     if value == 'none':
                #         req_vals[index] = None
                reqs[key] = (param_type, req_vals)
            elif param_type == 'anystring':
                reqs[key] = (param_type, [])
            else:
                print('invalid type, parsing failed for line: {}'.format(line))

    return col_locations, codenames, names, descriptions, reqs