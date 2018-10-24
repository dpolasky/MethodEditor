"""
Entry module for Python method editor. UI and file I/O.
#author: Daniel Polasky
#date: 10/16/2018
"""
import Parameters
from dataclasses import dataclass
import tkinter
from tkinter import filedialog
from tkinter import simpledialog
import os


optics_dict = {'sensitivity': 2,
               'resolution': 0,
               'high_resolution': 1}
param_descripts_file = 'param_descriptions.csv'


@dataclass
class Function(object):
    """
    Container to hold information for a single function
    """
    msms_mode: bool
    select_mz: float
    ms_start: float
    ms_end: float
    cv: float
    scantime: float
    start_time: float
    stop_time: float


def main_method_prep(param_obj_list):
    """
    Generate MS method files and sample list for a list of parameter containers. Allows
    all to be combined into a single method if desired (e.g. for droplet analysis) or
    to generate individual method files.
    :param param_obj_list: list of parameter containers for all analyses requested
    :type param_obj_list: list[Parameters.MethodParams]
    :return: void
    """
    if param_obj_list[0].combine_all_bool:
        # Combined mode: combine ALL analyses into a single method/raw file
        funcs = make_funcs(param_obj_list)
        filename = make_method_file(funcs, param_obj_list[0])
        sample_list_strings = [make_sample_list_component(param_obj_list[0], filename, funcs, current_index=1)]

    else:
        # standard mode - make an individual method file for each analysis (and split into multiple if requested)
        sample_list_strings = []
        sample_index = 1

        for param_obj in param_obj_list:
            funcs = make_funcs([param_obj])

            # Check if we need to split into multiple method files and perform the split if necessary
            if len(funcs) > param_obj.functions_per_file:
                # split the functions list into multiple method files
                multiple_methods = split_to_multiple_files(funcs, param_obj.functions_per_file)

                # generate the actual method files
                for func_list in multiple_methods:
                    filename = make_method_file(func_list, param_obj)
                    sample_list_part = make_sample_list_component(param_obj, filename, func_list, sample_index)
                    sample_list_strings.append(sample_list_part)
                    sample_index += 1

            else:
                # only one method/raw file for this parameter container - make it
                if len(funcs) >= 30:
                    simpledialog.messagebox.showerror('Too Many Functions!', 'Too many functions ({}) requested for combined file. MassLynx crashes hard above 30 files (due to hardware limitations in the electronics) so this is not allowed. Skipping this analysis.'.format(len(funcs)))
                    continue
                filename = make_method_file(funcs, param_obj)
                sample_list_part = make_sample_list_component(param_obj, filename, funcs, sample_index)
                sample_list_strings.append(sample_list_part)
                sample_index += 1

    # Generate sample list for all analyses
    make_final_sample_list(sample_list_strings, param_obj_list[0])


def make_sample_list_component(param_obj, exp_filename, func_list, current_index):
    """
    Generate a single line in the sample list for a given parameter container and function list. Depending on
    the settings. Returns a string that can be combined with any other sample
    list strings in the make_final_sample_list method.
    :param param_obj: parameter container
    :type param_obj: Parameters.MethodParams
    :param exp_filename: filename of the .exp file created by make_method_file
    :param func_list: lists of functions for sample text making
    :param current_index: current location in the sample list
    :return: string
    """
    output_string = ''
    cv_range = '{}-{}V'.format(func_list[0].cv, func_list[-1].cv)
    if param_obj.combine_all_bool:
        file_text = 'combined'
    else:
        file_text = cv_range
    filename = '{}_{}_{}_{}'.format(param_obj.date, param_obj.sample_name, func_list[0].select_mz, cv_range)

    line = '{},{},{},{},{}\n'.format(current_index, filename, file_text, exp_filename, param_obj.tune_file)

    current_index += 1
    output_string += line

    return output_string


def make_final_sample_list(sample_list_lines, param_obj):
    """
    Make a MassLynx sample list csv (to import) using provided lines and save location
    from a parameter container
    :param sample_list_lines: list of lines to put in the sample list
    :param param_obj: param container
    :type param_obj: Parameters.MethodParams
    :return: void
    """
    sample_list_name = 'csv_to_import.csv'
    if param_obj.save_to_masslynx:
        output_dir = param_obj.masslynx_dir
    else:
        output_dir = param_obj.output_dir
    sample_list_path = os.path.join(output_dir, sample_list_name)

    with open(sample_list_path, 'w') as samplefile:
        samplefile.write('Index,FILE_NAME,FILE_TEXT,MS_FILE,MS_TUNE_FILE\n')
        for line in sample_list_lines:
            samplefile.write(line)


def split_to_multiple_files(func_list, num_funcs_per_file):
    """
    Split the requested functions into multiple raw files if requested by the user. Appends
    a function into a raw file until the num_funcs_per_file is reached, then continues
    :param func_list: list of functions
    :param num_funcs_per_file: max number of functions per raw file
    :return: list of lists of functions
    :rtype: list[list[Function]]
    """
    func_counter = 1
    output_lists = []
    current_output_list = []

    for func in func_list:
        if func_counter > num_funcs_per_file:
            # Too many functions - start a new list
            output_lists.append([x for x in current_output_list])
            current_output_list = [func]
            func_counter = 1
        else:
            current_output_list.append(func)
            func_counter += 1
    output_lists.append(current_output_list)
    return output_lists


def make_method_file(function_list, param_obj):
    """
    Generate a .exp method file for MassLynx with the provided functions and parameters
    :param function_list: list of Function containers
    :type function_list: list[Function]
    :param param_obj: parameter container
    :type param_obj: Parameters.MethodParams
    :return: (string) name of the generated exp file
    """
    # Generate filename and path
    optic_short = param_obj.optic_mode[:1]
    cv_range = '{}-{}'.format(function_list[0].cv, function_list[-1].cv)
    if param_obj.combine_all_bool:
        exp_filename = '{}_{}_{}_{}V_{}min_{}V_COMBINED.exp'.format(param_obj.sample_name, param_obj.mz, optic_short, param_obj.cv_step, param_obj.collect_time, cv_range)
    else:
        exp_filename = '{}_{}_{}_{}V_{}min_{}V.exp'.format(param_obj.sample_name, param_obj.mz, optic_short, param_obj.cv_step, param_obj.collect_time, cv_range)
    if param_obj.save_to_masslynx:
        output_dir = param_obj.masslynx_dir
    else:
        output_dir = param_obj.output_dir
    exp_full_path = os.path.join(output_dir, exp_filename)

    # Write exp file from the provided base file
    header, func_lines, footer = get_basefile_lines(param_obj)

    # Header section
    output_lines = []
    for line in header:
        if line.lower().startswith('experimentduration'):
            newline = 'ExperimentDuration,{}\n'.format(function_list[-1].stop_time)
        elif line.lower().startswith('experimentcalibrationfilename'):
            newline = 'ExperimentCalibrationFilename,{},Enabled\n'.format(param_obj.cal_file)
        elif line.lower().startswith('opticmode'):
            newline = 'OpticMode,{}\n'.format(optics_dict[param_obj.optic_mode])
        elif line.lower().startswith('numberoffunctions'):
            newline = 'NumberOfFunctions,{}\n'.format(len(function_list))
        elif line.lower().startswith('functiontypes'):
            newline = get_func_types(function_list)
        else:
            newline = line
        output_lines.append(newline)

    # functions
    for index, func in enumerate(function_list):
        output_lines.extend(gen_function_lines(func, index + 1, func_lines, param_obj.optic_mode))

    # footer
    output_lines.extend(footer)

    # write output file
    with open(exp_full_path, 'w') as expfile:
        for line in output_lines:
            expfile.write(line)

    return exp_filename


def get_func_types(list_of_funcs):
    """
    Generate the function type string to pass to MassLynx from a given list of functions
    :param list_of_funcs: list of functions
    :type list_of_funcs: list[Function]
    :return: string
    """
    output_string = 'FunctionTypes'
    for func in list_of_funcs:
        if func.msms_mode:
            output_string += ',Tof MSMS'
        else:
            output_string += ',Tof MS'
    output_string += '\n'
    return output_string


def gen_function_lines(func, index, basefunc_lines, optic_mode):
    """
    Edit the lines from the basefile to generate a set of lines for the provided Function
    :param func: function container
    :type func: Function
    :param index: the function number (indexed from 1, not 0!)
    :param optic_mode: MethodParams.optic_mode (string)
    :param basefunc_lines: list of strings - lines from the base file for the function section
    :return: list of edited lines
    """
    output_lines = []
    for line in basefunc_lines:
        if line.lower().startswith('function '):
            newline = 'FUNCTION {}\n'.format(index)
        elif line.lower().startswith('useopticmode'):
            newline = 'UseOpticMode,{}\n'.format(optics_dict[optic_mode])
        elif line.lower().startswith('functionstarttime'):
            newline = 'FunctionStartTime(min),{}\n'.format(func.start_time)
        elif line.lower().startswith('functionendtime'):
            newline = 'FunctionEndTime(min),{}\n'.format(func.stop_time)
        elif line.lower().startswith('functionstartmass'):
            newline = 'FunctionStartMass,{}\n'.format(func.ms_start)
        elif line.lower().startswith('functionendmass'):
            newline = 'FunctionEndMass,{}\n'.format(func.ms_end)
        elif line.lower().startswith('functionscantime'):
            newline = 'FunctionScanTime(sec),{}\n'.format(func.scantime)
        elif line.lower().startswith('tofsetmass'):
            newline = 'TOFSetMass,{}\n'.format(func.select_mz)
        elif line.lower().startswith('tofcollisionenergy') or line.lower().startswith('fixedcollisionenergy'):
            # NOTE: CV param is different in MS vs MSMS mode. Correct ONLY the appropriate line and leave the other alone
            if func.msms_mode:
                if line.lower().startswith('tofcollisionenergy'):
                    newline = 'TOFCollisionEnergy,{}\n'.format(func.cv)
                else:
                    newline = line
            else:
                if line.lower().startswith('fixedcollisionenergy') and not line.lower().startswith('fixedcollisionenergy2'):
                    newline = 'FixedCollisionEnergy,{}\n'.format(func.cv)
                else:
                    newline = line
        else:
            newline = line

        output_lines.append(newline)
    return output_lines


def get_basefile_lines(param_obj):
    """
    Return lists of basefile lines for header, function, and footer
    :param param_obj: parameter container
    :type param_obj: Parameters.MethodParams
    :return: list of header, function, footer lines
    """
    header_lines, function_lines, footer_lines = [], ['\n'], []
    header = True
    footer = False
    with open(param_obj.base_file_path, 'r') as basefile:
        for line in list(basefile):
            # check where we are in the file
            if line.lower().startswith('function 1'):
                header = False
            
            # append line to appropriate list
            if header:
                header_lines.append(line)
            elif footer:
                footer_lines.append(line)
            else:
                function_lines.append(line)

            # check for end of function lines
            if param_obj.msms_bool:
                if line.lower().startswith('scanssum'):
                    footer = True
            else:
                if line.lower().startswith('fastddamsmsscantime'):
                    footer = True

            if line.lower().startswith('function 2'):
                print('WARNING: multiple functions in the base file; incorrect behavior possible')

    header_lines = header_lines[:-1]    # skip final blank line after header
    return header_lines, function_lines, footer_lines


def make_funcs(param_obj_list):
    """
    Generate a list of Function objects based on parameters supplied. Each method call produces
    A SINGLE output list of functions to generate a method file, so should be called each time
    a new output raw file will be produced.
    :param param_obj_list: list of all parameter objects to include in ONE OUTPUT method file
    :type param_obj_list: list[Parameters.MethodParams]
    :return: list of Function objects
    :rtype: list[Function]
    """
    funcs = []

    current_time = 0
    for param_obj in param_obj_list:
        current_voltage = param_obj.cv_start

        # delay time in use - generate all standard functions and delay functions
        if param_obj.delay_time_init > 0:
            init_delay_func = Function(msms_mode=param_obj.msms_bool,
                                       select_mz=param_obj.mz,
                                       ms_start=param_obj.ms_start,
                                       ms_end=param_obj.ms_end,
                                       cv=param_obj.cv_start,
                                       scantime=param_obj.scan_time,
                                       start_time=current_time,
                                       stop_time=current_time + param_obj.delay_time_init)
            funcs.append(init_delay_func)
            current_time += param_obj.delay_time_init

        while current_voltage <= param_obj.cv_end:
            # initialize each requested function
            start_time = current_time
            end_time = current_time + param_obj.collect_time
            funcs.append(Function(msms_mode=param_obj.msms_bool,
                                  select_mz=param_obj.mz,
                                  ms_start=param_obj.ms_start,
                                  ms_end=param_obj.ms_end,
                                  cv=current_voltage,
                                  scantime=param_obj.scan_time,
                                  start_time=start_time,
                                  stop_time=end_time))
            # increment parameters
            current_time += param_obj.collect_time
            current_voltage += param_obj.cv_step

    return funcs


def check_params_and_filepaths(param_obj_list, param_reqs, param_names):
    """
    Check that the user has input appropriate values for the parameters and filepaths
    to avoid crashing MassLynx
    :param param_obj_list: list of param containers
    :type param_obj_list: list[Parameters.MethodParams]
    :param param_names: dict of param key: display name for each parameter
    :param param_reqs: dict of param key: required value list for each parameter. Required values are [low, high] for numerical values or list of acceptable strings for strings
    :return: (bool) True for no problems, False if problems found
    """
    forbidden_chars = ['.', '  ', ':', '\\', '/', '?', '@', '~', '(', ')', ',', ';']

    for param_obj in param_obj_list:
        # check for forbidden characters in fields that will end up in filenames
        for char in forbidden_chars:
            if char in param_obj.date:
                simpledialog.messagebox.showerror('Forbidden Character', 'The character "{}" is not allowed in the DATE field to avoid crashing MassLynx. Canceling run.'.format(char))
                return False
            if char in param_obj.sample_name:
                simpledialog.messagebox.showerror('Forbidden Character', 'The character "{}" is not allowed in the SAMPLE NAME field to avoid crashing MassLynx. Canceling run.'.format(char))
                return False

        # check that all parameters are within allowed bounds
        if not check_all_param_vals(param_obj.params_dict, param_reqs, param_names):
            return False

        # make sure cal/tune/base files point at actual files
        if not os.path.exists(param_obj.base_file_path):
            simpledialog.messagebox.showerror('Invalid File Path','The provided base file path: {} does not point to a valid file! Canceling run.'.format(param_obj.base_file_path))
            return False
        if not os.path.exists(param_obj.cal_file):
            simpledialog.messagebox.showerror('Invalid File Path','The provided calibration file path: {} does not point to a valid file! Canceling run.'.format(param_obj.cal_file))
            return False
        if param_obj.save_to_masslynx:
            # check that the tune file exists in the provided AcquDB folder
            tune_path = os.path.join(param_obj.masslynx_dir, param_obj.tune_file)
            if not os.path.exists(tune_path):
                simpledialog.messagebox.showerror('Invalid File Path','The provided tune file path: {} does not point to a valid file! Canceling run.'.format(tune_path))
                return False

    return True


def check_all_param_vals(param_dict, par_reqs, par_names):
    """
    Check for any parameters in the input dictionary (from a single Parameters object) that
    are out of bounds. Returns True if all values are acceptable
    :param param_dict: dictionary of parameter key: value
    :param par_reqs: dict of parameter key, list of required values
    :param par_names: dict of parameter key, parameter name
    :return: (bool) True if no out-of-bounds
    """
    fail_params = []
    for param_key, value in param_dict.items():
        if not check_param_value(param_key, value, par_reqs):
            fail_params.append(param_key)

    if not len(fail_params) == 0:
        # some parameters failed. Tell the user which ones
        param_string = 'The parameter(s) below have inappropriate values. This analysis will be skipped. Press OK to continue\n'
        for param in fail_params:
            if par_reqs[param][0] == 'string' or par_reqs[param][0] == 'bool':
                # print acceptable values list for string/bool
                vals_string = ', '.join(par_reqs[param][1])
                param_string += '{}: value must be one of ({})\n'.format(par_names[param], vals_string)
            else:
                # print type and bounds for float/int
                lower_bound = par_reqs[param][1][0]
                upper_bound = par_reqs[param][1][1]
                param_string += '{}:\n\t Value Type must be: {}\n\t Value must be within bounds: {} - {}\n'.format(par_names[param],
                                                                                                                   par_reqs[param][0],
                                                                                                                   lower_bound,
                                                                                                                   upper_bound)
        simpledialog.messagebox.showwarning(title='Parameter Error', message=param_string)
        return False
    # no failures
    return True


def check_param_value(param_key, entered_val, par_reqs):
    """
    Check an individual parameter against its requirements
    :param param_key: key to parameter dictionary to be checked
    :param entered_val: value to check
    :param par_reqs: dict of parameter key, list of required values
    :return: True if the current value of the corresponding entry is valid, False if not
    """
    param_type = par_reqs[param_key][0]
    param_val_list = par_reqs[param_key][1]
    if param_type == 'int':
        # If the param is an int, the value must be within the values specified in the requirement tuple
        return param_val_list[0] <= entered_val <= param_val_list[1]

    elif param_type == 'float':
        return param_val_list[0] <= entered_val <= param_val_list[1]

    elif param_type == 'string' or param_type == 'bool':
        check_val_list = [x.strip().lower() for x in param_val_list]    # check against lower case/stripped
        return str(entered_val).lower() in check_val_list

    elif param_type == 'anystring':
        # Things like titles can be any string - no checking required
        return True


def main(template_file):
    """
    Run Method editor for the provided template file
    :param template_file: path to template csv file to process
    :return: void
    """
    # for template_file in list_of_template_files:
    list_of_param_objs, param_reqs, param_names = Parameters.parse_params_template_csv(template_file, param_descripts_file)
    if check_params_and_filepaths(list_of_param_objs, param_reqs, param_names):
        main_method_prep(list_of_param_objs)

        if list_of_param_objs[0].save_to_masslynx:
            simpledialog.messagebox.showinfo('Success!', 'Method files were generated successfully! To run the generated method(s), import the "csv-to-import.csv" file into MassLynx (File/Import Worksheet) to load the created sample list.\n\nMethod files saved to {}'.format(list_of_param_objs[0].masslynx_dir))
        else:
            simpledialog.messagebox.showinfo('Success!', 'Method files generated successfully. To run the generated method(s), import the "csv-to-import.csv" file into MassLynx (File/Import Worksheet) to load the created sample list. \n\nNOTE: "Save to MassLynx?" was set to False, so generated files MUST be moved to the MassLynx\<your project>.Pro\ACQUDB folder before running the sample list in MassLynx!\n\nOutput method files were saved to {}'.format(list_of_param_objs[0].output_dir))


if __name__ == '__main__':
    root = tkinter.Tk()
    root.withdraw()

    templatefile = filedialog.askopenfilename(title='Choose Template File(s)', filetypes=[('CSV Files', '.csv')])
    main(templatefile)

