"""
Entry module for Python method editor. UI and file I/O.
#author: Daniel Polasky
#date: 10/16/2018
"""
import Parameters
from dataclasses import dataclass
import tkinter
from tkinter import filedialog
import os


optics_dict = {'sensitivity': 2,
               'resolution': 0,
               'high_resolution': 1}

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
    optic_mode: str


def main_make_method(param_obj):
    """
    Generate MS method files and sample list for a given parameter container
    :param param_obj: parameter container
    :type param_obj: Parameters.MethodParams
    :return: void
    """
    funcs = make_funcs(param_obj)

    # Check if we need to split into multiple method files and perform the split if necessary
    if not param_obj.delay_bool:
        if len(funcs) > param_obj.functions_per_file:
            # split the functions list into multiple method files
            method_func_lists = split_to_multiple_files(funcs, param_obj.functions_per_file)
        else:
            method_func_lists = [funcs]
    else:
        # If delay in use, only one output file
        method_func_lists = [funcs]

    # Generate MS method files and associated sample list
    ms_filenames = []
    for func_list in method_func_lists:
        filename = make_method_file(func_list, param_obj)
        ms_filenames.append(filename)
    make_sample_list(param_obj, ms_filenames, method_func_lists)


def make_sample_list(param_obj, exp_filenames, method_func_lists):
    """
    Make a MassLynx sample list csv (to import) using provided parameters and filenames
    :param param_obj: parameter container
    :type param_obj: Parameters.MethodParams
    :param exp_filenames: list of filenames
    :param method_func_lists: list of lists of functions for sample text making
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
        for index, exp_filename in enumerate(exp_filenames):
            cv_range = '{}-{}V'.format(method_func_lists[index][0].cv, method_func_lists[index][-1].cv)
            if param_obj.delay_bool:
                file_text = 'delay_multiple_FPs'
            else:
                file_text = cv_range
            filename = '{}_{}_{}_{}'.format(param_obj.date, param_obj.sample_name, method_func_lists[index][0].select_mz, cv_range)

            line = '{},{},{},{},{}\n'.format(index + 1, filename, file_text, exp_filename, param_obj.tune_file)
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
    exp_filename = '{}_{}_{}_{}V_{}min_{}V.exp'.format(param_obj.sample_name, param_obj.mz, optic_short, param_obj.cv_step, param_obj.collect_time, cv_range)
    if param_obj.save_to_masslynx:
        output_dir = param_obj.masslynx_dir
    else:
        output_dir = param_obj.output_dir
    exp_full_path = os.path.join(output_dir, exp_filename)

    # Write exp file from the provided base file
    header, func_lines, footer = get_basefile_lines(param_obj.base_file_path)

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
            if param_obj.msms_bool:
                newline = 'FunctionsTypes,{}\n'.format(','.join(['Tof MSMS' for _ in range(len(function_list))]))
            else:
                newline = 'FunctionsTypes,{}\n'.format(','.join(['Tof MS' for _ in range(len(function_list))]))
        else:
            newline = line
        output_lines.append(newline)

    # functions
    for index, func in enumerate(function_list):
        output_lines.extend(gen_function_lines(func, index + 1, func_lines, param_obj))

    # footer
    output_lines.extend(footer)

    # write output file
    with open(exp_full_path, 'w') as expfile:
        for line in output_lines:
            expfile.write(line)

    return exp_filename


def gen_function_lines(func, index, basefunc_lines, param_obj):
    """
    Edit the lines from the basefile to generate a set of lines for the provided Function
    :param func: function container
    :type func: Function
    :param index: the function number (indexed from 1, not 0!)
    :param param_obj: parameter container
    :type param_obj: Parameters.MethodParams
    :param basefunc_lines: list of strings - lines from the base file for the function section
    :return: list of edited lines
    """
    output_lines = []
    for line in basefunc_lines:
        if line.lower().startswith('function '):
            newline = 'Function {}\n'.format(index)
        elif line.lower().startswith('useopticmode'):
            newline = 'UseOpticMode,{}\n'.format(optics_dict[param_obj.optic_mode])
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
        elif line.lower().startswith('tofcollisionenergy'):
            newline = 'TOFCollisionEnergy,{}\n'.format(func.cv)   # MSMS mode
        elif line.lower().startswith('fixedcollisionenergy'):
            newline = 'FixedCollisionEnergy,{}\n'.format(func.cv) # MS mode
        else:
            newline = line

        output_lines.append(newline)
    return output_lines


def get_basefile_lines(basefile_path):
    """
    Return lists of basefile lines for header, function, and footer
    :param basefile_path: full path to basefile to read
    :return: list of header, function, footer lines
    """
    header_lines, function_lines, footer_lines = [], ['\n'], []
    header = True
    footer = False
    with open(basefile_path, 'r') as basefile:
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

            if line.lower().startswith('scanssum'):
                footer = True

            if line.lower().startswith('function 2'):
                print('WARNING: multiple functions in the base file; incorrect behavior possible')

    header_lines = header_lines[:-1]    # skip final blank line after header
    return header_lines, function_lines, footer_lines


def make_funcs(param_obj):
    """
    Generate a list of Function objects based on parameters supplied. Default method - no delays
    or fancy handling.
    :param param_obj: parameter container
    :type param_obj: Parameters.MethodParams
    :return: list of Function objects
    :rtype: list[Function]
    """
    funcs = []

    # if not param_obj.delay_bool:
        # standard method with no delays - simply generate a function for each voltage step
    current_voltage = param_obj.cv_start
    current_time = 0

    # delay time in use - generate all standard functions and delay functions
    if param_obj.delay_bool:
        init_delay_func = Function(msms_mode=param_obj.msms_bool,
                                   select_mz=param_obj.mz,
                                   ms_start=param_obj.ms_start,
                                   ms_end=param_obj.ms_end,
                                   cv=param_obj.cv_start,
                                   scantime=param_obj.scan_time,
                                   start_time=current_time,
                                   stop_time=param_obj.delay_time_init,
                                   optic_mode=param_obj.optic_mode)
        funcs.append(init_delay_func)
        current_time = param_obj.delay_time_init

    while current_voltage <= param_obj.cv_end:
        # initialize new function
        start_time = current_time
        end_time = current_time + param_obj.collect_time
        funcs.append(Function(msms_mode=param_obj.msms_bool,
                              select_mz=param_obj.mz,
                              ms_start=param_obj.ms_start,
                              ms_end=param_obj.ms_end,
                              cv=current_voltage,
                              scantime=param_obj.scan_time,
                              start_time=start_time,
                              stop_time=end_time,
                              optic_mode=param_obj.optic_mode))
        # increment parameters
        current_time += param_obj.collect_time
        current_voltage += param_obj.cv_step
    # else:
    #     # delay time in use - generate all standard functions and delay functions
    #     init_delay_func = Function(msms_mode=param_obj.msms_bool,
    #                               select_mz=param_obj.mz,
    #                               ms_start=param_obj.ms_start,
    #                               ms_end=param_obj.ms_end,
    #                               cv=param_obj.cv_start,
    #                               scantime=param_obj.scan_time,
    #                               start_time=0.0,
    #                               stop_time=param_obj.delay_time_init,
    #                               optic_mode=param_obj.optic_mode)
    #     funcs.append(init_delay_func)
    #
    #     # prepare remaining functions
    #     current_voltage = param_obj.cv_start
    #     current_time = param_obj.delay_time_init
    #     while current_voltage <= param_obj.cv_end:
    #         # initialize new function
    #         start_time = current_time
    #         end_time = current_time + param_obj.collect_time
    #         funcs.append(Function(msms_mode=param_obj.msms_bool,
    #                               select_mz=param_obj.mz,
    #                               ms_start=param_obj.ms_start,
    #                               ms_end=param_obj.ms_end,
    #                               cv=current_voltage,
    #                               scantime=param_obj.scan_time,
    #                               start_time=start_time,
    #                               stop_time=end_time,
    #                               optic_mode=param_obj.optic_mode))
    #
    #         # increment parameters
    #         current_time += param_obj.collect_time
    #         current_voltage += param_obj.cv_step
    #
    #         # add a delay function in between data functions if desired
    #         if param_obj.delay_time_btwn > 0:
    #             funcs.append(Function(msms_mode=param_obj.msms_bool,
    #                                   select_mz=param_obj.mz,
    #                                   ms_start=param_obj.ms_start,
    #                                   ms_end=param_obj.ms_end,
    #                                   cv=current_voltage,
    #                                   scantime=param_obj.scan_time,
    #                                   start_time=current_time,
    #                                   stop_time=current_time + param_obj.delay_time_btwn,
    #                                   optic_mode=param_obj.optic_mode))
    #             current_time += param_obj.delay_time_btwn

    return funcs


if __name__ == '__main__':
    root = tkinter.Tk()
    root.withdraw()

    param_files = filedialog.askopenfilenames(title='Choose Config Files', filetypes=[('Text Files', '.txt')])

    for param_file in param_files:
        param_container = Parameters.MethodParams(param_file)
        main_make_method(param_container)
