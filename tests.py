"""
Testing module for generated method files. Not strict unit test - instead, uses several
created MassLynx method files for each major scenario (MS vs MSMS, G1 vs G2, etc) and checks
whether the created .exp file matches the MassLynx version exactly for debugging/fixing.
#author: Daniel Polasky
#date: 10/17/2018
"""

test_folder = 'test_files'

from dataclasses import dataclass
import os
import MethodEditor_Main
import Parameters


@dataclass
class Test(object):
    """
    Test container. Holds paths to input and output files for convenient automation
    """
    template_file: str      # template CSV to generate the expected output
    base_file: str          # base file to use to generate output
    masslynx_exp_file: str  # comparison file to compare to output
    test_dir: str           # directory in which to save output for reference

    def run_test(self):
        """
        Run method editor and compare output to the masslynx file
        :return:
        """
        params_list = Parameters.parse_params_template_csv(self.template_file, MethodEditor_Main.param_descripts_file)

        # save output to test directory
        for param_obj in params_list:
            param_obj.save_to_masslynx = False
            param_obj.output_dir = self.test_dir

        MethodEditor_Main.main_method_prep(params_list)

        # load generated exp file
        exp_outputs = [x for x in os.listdir(self.test_dir) if x.endswith('.exp')]
        test_output = [os.path.join(self.test_dir, x) for x in exp_outputs if ('basefile' not in x and 'masslynx' not in x)][0]

        # compare against masslynx file
        success_flag = compare_exps(masslynx_file=self.masslynx_exp_file, output_file=test_output)
        return success_flag


def compare_exps(masslynx_file, output_file):
    """
    Compare a generated experiment file against a MassLynx one to ensure no differences are present.
    :param masslynx_file: exp file
    :param output_file: exp file
    :return: prints output to console
    """
    success_flag = True
    with open(masslynx_file, 'r') as mlfile:
        masslynx_lines = list(mlfile)

    with open(output_file, 'r') as testfile:
        for index, line in enumerate(list(testfile)):
            if not masslynx_lines[index] == line:
                # check for just int/decimal diffs (1 vs 1.0)
                splits = line.split(',')
                try:
                    intval = int(float(splits[1].rstrip('\n')))
                except ValueError:
                    intval = 'nope'
                newline = '{},{}\n'.format(splits[0], intval)
                if not masslynx_lines[index] == newline:
                    success_flag = False
                    print('****** Mismatch at line {}   (masslynx first, then ME output)\n{}{}'.format(index + 1, masslynx_lines[index], line.rstrip('\n')))

    return success_flag


def main_tests():
    """
    Run all tests according to framework
    :return: void
    """
    full_path = os.path.join(os.getcwd(), test_folder)
    test_dirs = [os.path.join(full_path, x) for x in os.listdir(full_path) if os.path.isdir(os.path.join(full_path, x))]

    for test_dir in test_dirs:
        clean_old_tests(test_dir)

        # ensure test dir isn't empty (placeholder for future tests)
        if len(os.listdir(test_dir)) > 0:
            # create a test object with the files in this test directory
            basefile = [os.path.join(test_dir, x) for x in os.listdir(test_dir) if 'basefile' in x.lower()][0]
            template = [os.path.join(test_dir, x) for x in os.listdir(test_dir) if 'template' in x.lower()][0]
            masslynx = [os.path.join(test_dir, x) for x in os.listdir(test_dir) if 'masslynx' in x.lower()][0]
            test = Test(template_file=template, base_file=basefile, masslynx_exp_file=masslynx, test_dir=test_dir)

            # run the test
            print('\nStarting test for {}'.format(os.path.basename(test_dir)))
            success = test.run_test()
            if success:
                print('SUCCESS for test: {}'.format(os.path.basename(test_dir)))
            else:
                print('FAIL for test: {}'.format(os.path.basename(test_dir)))


def clean_old_tests(test_dir):
    """
    Remove any previous .exp files generated during testing by removing any chars that
    have an asterisk
    :param test_dir: directory to clean
    :return: void
    """
    for file in os.listdir(test_dir):
        if 'qqq' in file:
            os.remove(os.path.join(test_dir, file))


if __name__ == '__main__':
    main_tests()
