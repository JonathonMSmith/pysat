#!/usr/bin/env python
# Full license can be found in License.md
# Full author list can be found in .zenodo.json file
# DOI:10.5281/zenodo.1199703
#
# DISTRIBUTION STATEMENT A: Approved for public release. Distribution is
# unlimited.
# This work was supported by the Office of Naval Research.
# ----------------------------------------------------------------------------
"""Standardized class and functions to test instruments for pysat libraries.

Note
----
Not directly called by pytest, but imported as part of test_instruments.py.
Can be imported directly for external instrument libraries of pysat instruments.

Examples
--------
::

    # Import custom instrument library
    import mypackage

    # Import the test classes from pysat.
    from pysat.tests.classes.cls_instrument_library import InstLibTests

    InstLibTests.initialize_test_package(InstLibTests,
                                         inst_loc=mypackage.instruments,
                                         user_info=user_info)

    class TestInstruments(InstLibTests):
        '''Create a testable object from standard library.

        Note
        -----
        In your docstring be sure to use double quotes instead of single quotes.

        '''

"""

import datetime as dt
from importlib import import_module
import logging
import numpy as np
import sys
import tempfile
import warnings

import pandas as pds
import pytest
import xarray as xr

import pysat
from pysat.utils import generate_instrument_list
from pysat.utils import testing


def initialize_test_inst_and_date(inst_dict):
    """Initialize the instrument object to test and date.

    Parameters
    ----------
    inst_dict : dict
        Dictionary containing specific instrument info, generated by
        generate_instrument_list

    Returns
    -------
    test_inst : pysat.Instrument
        instrument object to be tested
    date : dt.datetime
        test date from module

    """

    kwargs = inst_dict['kwargs'] if 'kwargs' in inst_dict.keys() else {}
    test_inst = pysat.Instrument(inst_module=inst_dict['inst_module'],
                                 tag=inst_dict['tag'],
                                 inst_id=inst_dict['inst_id'],
                                 temporary_file_list=True, update_files=True,
                                 **kwargs)
    test_dates = inst_dict['inst_module']._test_dates
    date = test_dates[inst_dict['inst_id']][inst_dict['tag']]
    return test_inst, date


def load_and_set_strict_time_flag(test_inst, date, raise_error=False,
                                  clean_off=True, set_end_date=False):
    """Load data and set the strict time flag if needed for other tests.

    Parameters
    ----------
    test_inst : pysat.Instrument
        Test instrument
    date : dt.datetime
        Date for loading data
    raise_error : bool
        Raise the load error if it is not the strict time flag error
        (default=False)
    clean_off : bool
        Turn off the clean method when re-loading data and testing the
        strict time flag (default=True)
    set_end_date : bool
        If True, load with setting the end date. If False, load single day.
        (default=False)

    """

    kwargs = {}

    if set_end_date:
        kwargs['end_date'] = date + dt.timedelta(days=2)

    try:
        test_inst.load(date=date, **kwargs)
    except Exception as err:
        # Catch all potential input errors, and only ensure that the one caused
        # by the strict time flag is prevented from occurring on future load
        # calls.
        if str(err).find('Loaded data') > 0:
            # Change the flags that may have caused the error to be raised, to
            # see if it the strict time flag
            test_inst.strict_time_flag = False

            if clean_off:
                # Turn the clean method off
                orig_clean_level = str(test_inst.clean_level)
                test_inst.clean_level = 'none'

            # Evaluate the warning
            with warnings.catch_warnings(record=True) as war:
                test_inst.load(date=date, **kwargs)

            assert len(war) >= 1
            categories = [war[j].category for j in range(len(war))]
            assert UserWarning in categories

            if clean_off:
                # Reset the clean level
                test_inst.clean_level = orig_clean_level
        elif raise_error:
            raise err

    return


class InstLibTests(object):
    """Provide standardized tests for pysat instrument libraries.

    Note
    ----
    Uses class level setup and teardown so that all tests use the same
    temporary directory. We do not want to geneate a new tempdir for each test,
    as the load tests need to be the same as the download tests.

    Not directly run by pytest, but inherited through test_instruments.py

    Users will need to run `initialize_test_package` before setting up the test
    class.

    See Also
    --------
    `pysat.tests.test_instruments`

    """

    # Define standard attributes to check.
    # Needs to be defined here for backwards compatibility.
    module_attrs = ['platform', 'name', 'tags', 'inst_ids',
                    'load', 'list_files', 'download']
    inst_attrs = ['tag', 'inst_id', 'acknowledgements', 'references',
                  'inst_module']
    inst_callable = ['load', 'list_files', 'download', 'clean',
                     'default']
    attr_types = {'platform': str, 'name': str, 'tags': dict,
                  'inst_ids': dict, 'tag': str, 'inst_id': str,
                  'acknowledgements': str, 'references': str}

    def setup_class(self):
        """Initialize the testing setup once before all tests are run."""

        # Use a temporary directory so that the user's setup is not altered.
        # TODO(#974): Remove if/else when support for Python 3.9 is dropped.
        if sys.version_info.minor >= 10:
            self.tempdir = tempfile.TemporaryDirectory(
                ignore_cleanup_errors=True)
        else:
            self.tempdir = tempfile.TemporaryDirectory()
        self.saved_path = pysat.params['data_dirs']
        pysat.params._set_data_dirs(path=self.tempdir.name, store=False)
        return

    def teardown_class(self):
        """Clean up downloaded files and parameters from tests."""

        pysat.params._set_data_dirs(self.saved_path, store=False)
        # Remove the temporary directory. In Windows, this occasionally fails
        # by raising a wide variety of different error messages. Python 3.10+
        # can handle this, but lower Python versions cannot.
        # TODO(#974): Remove try/except when support for Python 3.9 is dropped.
        try:
            self.tempdir.cleanup()
        except Exception:
            pass

        del self.saved_path, self.tempdir
        return

    def setup_method(self):
        """Initialize parameters before each method."""
        self.test_inst = None
        self.date = None

        return

    def teardown_method(self):
        """Clean up any instruments that were initialized."""

        del self.test_inst, self.date

        return

    def initialize_test_package(self, inst_loc, user_info=None):
        """Generate custom instrument lists for each category of tests.

        Parameters
        ----------
        inst_loc : python subpackage
            The location of the instrument subpackage to test, e.g.,
            `pysat.instruments`
        user_info : dict or NoneType
            Nested dictionary with user and password info for instrument module
            name.  If None, no user or password is assumed. (default=None)
            EX: user_info = {'jro_isr': {'user': 'myname', 'password': 'email'}}

        Returns
        -------
        instruments : dict
            A dictionary containing the lists of instruments from a given
            package for each category of tests.  The categories are:
            "names" : A list of all insrument modules by name.
            "download" : Instrument objects with full download support.
            "no_download" : Instrument objects without download support.

        """

        # Attach location of package to test object for later reference.
        self.inst_loc = inst_loc

        # Find all instruments for testing from user-specified location.
        instruments = generate_instrument_list(inst_loc=inst_loc,
                                               user_info=user_info)

        # Find all methods in the standard test class.
        method_list = [func for func in dir(self)
                       if callable(getattr(self, func))]

        # Search tests for iteration via pytestmark, update w/ instrument list.
        for method in method_list:
            if hasattr(getattr(self, method), 'pytestmark'):
                # Get list of names of pytestmarks.
                n_args = len(getattr(self, method).pytestmark)
                mark_names = [getattr(self, method).pytestmark[j].name
                              for j in range(0, n_args)]

                # Add instruments from your library.
                if 'all_inst' in mark_names:
                    mark = pytest.mark.parametrize("inst_name",
                                                   instruments['names'])
                    getattr(self, method).pytestmark.append(mark)
                elif 'new_tests' in mark_names:
                    # Prioritize new test marks if present
                    mark = pytest.mark.parametrize("inst_dict",
                                                   instruments['new_tests'])
                    getattr(self, method).pytestmark.append(mark)
                elif 'load_options' in mark_names:
                    # Prioritize load_options mark if present
                    mark = pytest.mark.parametrize("inst_dict",
                                                   instruments['load_options'])
                    getattr(self, method).pytestmark.append(mark)
                elif 'download' in mark_names:
                    mark = pytest.mark.parametrize("inst_dict",
                                                   instruments['download'])
                    getattr(self, method).pytestmark.append(mark)
                elif 'no_download' in mark_names:
                    mark = pytest.mark.parametrize("inst_dict",
                                                   instruments['no_download'])
                    getattr(self, method).pytestmark.append(mark)

        return instruments

    @pytest.mark.all_inst
    def test_modules_standard(self, inst_name):
        """Test that modules are importable and have standard properties.

        Parameters
        ----------
        inst_name : str
            Name of instrument module.  Set automatically from
            instruments['names'] when `initialize_test_package` is run.

        """

        # Ensure that each module is at minimum importable
        module = import_module(''.join(('.', inst_name)),
                               package=self.inst_loc.__name__)

        # Check for presence of basic instrument module attributes
        for mattr in self.module_attrs:
            testing.assert_hasattr(module, mattr)
            if mattr in self.attr_types.keys():
                testing.assert_isinstance(getattr(module, mattr),
                                          self.attr_types[mattr])

        # Check for presence of required instrument attributes
        for inst_id in module.inst_ids.keys():
            for tag in module.inst_ids[inst_id]:
                inst = pysat.Instrument(inst_module=module, tag=tag,
                                        inst_id=inst_id)

                # Test to see that the class parameters were passed in
                testing.assert_isinstance(inst, pysat.Instrument)
                assert inst.platform == module.platform
                assert inst.name == module.name
                assert inst.inst_id == inst_id
                assert inst.tag == tag
                assert inst.inst_module is not None

                # Test the required class attributes
                for iattr in self.inst_attrs:
                    testing.assert_hasattr(inst, iattr)
                    if iattr in self.attr_types:
                        testing.assert_isinstance(getattr(inst, iattr),
                                                  self.attr_types[iattr])
        return

    @pytest.mark.all_inst
    def test_standard_function_presence(self, inst_name):
        """Test that each function is callable, all required functions exist.

        Parameters
        ----------
        inst_name : str
            Name of instrument module.  Set automatically from
            instruments['names'] when `initialize_test_package` is run.

        """

        module = import_module(''.join(('.', inst_name)),
                               package=self.inst_loc.__name__)

        # Test for presence of all standard module functions
        for mcall in self.inst_callable:
            if hasattr(module, mcall):
                # If present, must be a callable function
                assert callable(getattr(module, mcall))
            else:
                # If absent, must not be a required function
                assert mcall not in self.module_attrs
        return

    @pytest.mark.all_inst
    def test_instrument_test_dates(self, inst_name):
        """Test that module has structured test dates correctly.

        Parameters
        ----------
        inst_name : str
            Name of instrument module.  Set automatically from
            instruments['names'] when `initialize_test_package` is run.

        """

        module = import_module(''.join(('.', inst_name)),
                               package=self.inst_loc.__name__)
        info = module._test_dates
        for inst_id in info.keys():
            for tag in info[inst_id].keys():
                testing.assert_isinstance(info[inst_id][tag], dt.datetime)
        return

    @pytest.mark.first
    @pytest.mark.download
    def test_download(self, inst_dict):
        """Test that instruments are downloadable.

        Parameters
        ----------
        inst_dict : dict
            Dictionary containing info to instantiate a specific instrument.
            Set automatically from instruments['download'] when
            `initialize_test_package` is run.

        """

        self.test_inst, self.date = initialize_test_inst_and_date(inst_dict)

        # Check for username.
        if 'user_info' in inst_dict.keys():
            dl_dict = inst_dict['user_info']
        else:
            dl_dict = {}

        # Ask to download two consecutive days
        self.test_inst.download(start=self.date,
                                stop=self.date + dt.timedelta(days=2),
                                **dl_dict)
        assert len(self.test_inst.files.files) > 0
        return

    @pytest.mark.second
    @pytest.mark.load_options
    @pytest.mark.parametrize("clean_level", ['none', 'dirty', 'dusty', 'clean'])
    def test_load(self, clean_level, inst_dict):
        """Test that instruments load at each cleaning level.

        Parameters
        ----------
        clean_level : str
            Cleanliness level for loaded instrument data.
        inst_dict : dict
            Dictionary containing info to instantiate a specific instrument.
            Set automatically from instruments['download'] when
            `initialize_test_package` is run.

        """

        self.test_inst, self.date = initialize_test_inst_and_date(inst_dict)
        if len(self.test_inst.files.files) > 0:
            # Set the clean level
            self.test_inst.clean_level = clean_level
            target = 'Fake Data to be cleared'
            self.test_inst.data = [target]

            # Make sure the strict time flag doesn't interfere with
            # the load tests, and re-run with desired clean level
            load_and_set_strict_time_flag(self.test_inst, self.date,
                                          raise_error=True, clean_off=False)

            # Make sure fake data is cleared
            assert target not in self.test_inst.data

            # If cleaning not used, something should be in the file
            # Not used for clean levels since cleaning may remove all data
            if clean_level == "none":
                assert not self.test_inst.empty
        else:
            pytest.skip("Download data not available")

        return

    @pytest.mark.second
    @pytest.mark.load_options
    def test_load_empty(self, inst_dict):
        """Test that instruments load empty objects if no data is available.

        Parameters
        ----------
        inst_dict : dict
            Dictionary containing info to instantiate a specific instrument.
            Set automatically from instruments['download'] when
            `initialize_test_package` is run.

        """

        # Get the instrument information and update the date to be in the future
        self.test_inst, self.date = initialize_test_inst_and_date(inst_dict)
        self.date = dt.datetime(dt.datetime.utcnow().year + 100, 1, 1)

        # Make sure the strict time flag doesn't interfere with the load test
        load_and_set_strict_time_flag(self.test_inst, self.date,
                                      raise_error=True)

        # Check the empty status
        assert self.test_inst.empty, "Data was loaded for a far-future time"
        assert self.test_inst.meta == pysat.Meta(), "Meta data is not empty"
        if self.test_inst.pandas_format:
            assert all(self.test_inst.data == pds.DataFrame()), "Data not empty"
        else:
            assert self.test_inst.data.dims == xr.Dataset().dims, \
                "Dims not empty"
            assert self.test_inst.data.data_vars == xr.Dataset().data_vars, \
                "Data variables not empty"

        return

    # TODO(v3.3.0): remove mark.new_tests when ecosystem is fully compliant
    # for this test
    @pytest.mark.second
    @pytest.mark.load_options
    @pytest.mark.new_tests
    def test_load_multiple_days(self, inst_dict):
        """Test that instruments load at each cleaning level.

        Parameters
        ----------
        inst_dict : dict
            Dictionary containing info to instantiate a specific instrument.
            Set automatically from instruments['download'] when
            `initialize_test_package` is run.

        """

        self.test_inst, self.date = initialize_test_inst_and_date(inst_dict)
        if len(self.test_inst.files.files) > 0:
            if self.date < self.test_inst.today():
                # Make sure the strict time flag doesn't interfere with
                # the load tests, and re-run with desired clean level
                load_and_set_strict_time_flag(self.test_inst, self.date,
                                              raise_error=True, clean_off=False,
                                              set_end_date=True)

                # Make sure more than one day has been loaded
                assert hasattr(self.test_inst.index, 'day'), \
                    "No data to load for {:}-{:}".format(
                        self.date, self.date + dt.timedelta(days=2))
                assert len(np.unique(self.test_inst.index.day)) > 1
            else:
                pytest.skip("".join(["Can't download multiple days of real-",
                                     "time or forecast data"]))
        else:
            pytest.skip("Download data not available")

        return

    @pytest.mark.second
    @pytest.mark.load_options
    @pytest.mark.parametrize("clean_level", ['dirty', 'dusty', 'clean'])
    def test_clean_warn(self, clean_level, inst_dict, caplog):
        """Test that appropriate warnings and errors are raised when cleaning.

        Parameters
        ----------
        clean_level : str
            Cleanliness level for loaded instrument data.
        inst_dict : dict
            Dictionary containing info to instantiate a specific instrument.
            Set automatically from instruments['download'] when
            `initialize_test_package` is run.

        """
        # Not all Instruments have warning messages to test, only run tests
        # when the desired test attribute is defined
        if hasattr(inst_dict['inst_module'], '_clean_warn'):
            clean_warn = inst_dict['inst_module']._clean_warn[
                inst_dict['inst_id']][inst_dict['tag']]

            # Cleaning warnings may vary by clean level, test the warning
            # messages at the current clean level, specified by `clean_level`
            if clean_level in clean_warn.keys():
                # Only need to test if there are clean warnings for this level
                self.test_inst, self.date = initialize_test_inst_and_date(
                    inst_dict)
                clean_warnings = clean_warn[clean_level]

                # Make sure the strict time flag doesn't interfere with
                # the cleaning tests
                load_and_set_strict_time_flag(self.test_inst, self.date)

                # Cycle through each of the potential cleaning messages
                # for this Instrument module, inst ID, tag, and clean level
                for (clean_method, clean_method_level, clean_method_msg,
                     final_level) in clean_warnings:
                    if len(self.test_inst.files.files) > 0:
                        # Set the clean level
                        self.test_inst.clean_level = clean_level
                        target = 'Fake Data to be cleared'
                        self.test_inst.data = [target]

                        if clean_method == 'logger':
                            # A logging message is expected
                            with caplog.at_level(
                                    getattr(logging, clean_method_level),
                                    logger='pysat'):
                                self.test_inst.load(date=self.date)

                            # Test the returned message
                            out_msg = caplog.text
                            assert out_msg.find(clean_method_msg) >= 0, \
                                "{:s} not in output: {:s}".format(
                                    clean_method_msg, out_msg)
                        elif clean_method == 'warning':
                            # A warning message is expected
                            with warnings.catch_warnings(record=True) as war:
                                self.test_inst.load(date=self.date)

                            # Test the warning output
                            testing.eval_warnings(war, [clean_method_msg],
                                                  clean_method_level)
                        elif clean_method == 'error':
                            # An error message is expected, evaluate error
                            # and the error message
                            testing.eval_bad_input(
                                self.test_inst.load, clean_method_level,
                                clean_method_msg,
                                input_kwargs={'date': self.date})
                        else:
                            raise AttributeError(
                                'unknown type of warning: {:}'.format(
                                    clean_method))

                        # Test to see if the clean flag has the expected value
                        # afterwards
                        assert self.test_inst.clean_level == final_level, \
                            "Clean level should now be {:s}, not {:s}".format(
                                final_level, self.test_inst.clean_level)

                        # Make sure fake data is cleared
                        assert target not in self.test_inst.data
                    else:
                        pytest.skip("".join(["Can't test clean warnings for ",
                                             "Instrument ",
                                             repr(inst_dict['inst_module']),
                                             " level ", clean_level,
                                             " (no downloaded files)"]))
            else:
                pytest.skip("".join(["No clean warnings for Instrument ",
                                     repr(inst_dict['inst_module']), " level ",
                                     clean_level]))
        else:
            pytest.skip("No clean warnings for Instrument {:s}".format(
                repr(inst_dict['inst_module'])))

        return

    # TODO(v3.3.0): remove mark.new_tests when ecosystem is fully compliant
    # for this test
    @pytest.mark.second
    @pytest.mark.load_options
    @pytest.mark.new_tests
    @pytest.mark.parametrize('pad', [{'days': 1}, dt.timedelta(days=1)])
    def test_load_w_pad(self, pad, inst_dict):
        """Test that instruments load at each cleaning level.

        Parameters
        ----------
        pad : pds.DateOffset, dict, or NoneType
            Valid pad value for initializing an instrument
        inst_dict : dict
            Dictionary containing info to instantiate a specific instrument.
            Set automatically from instruments['download'] when
            `initialize_test_package` is run.

        """
        # Skip for Python 3.6, keeping information that will allow adding
        # or skipping particular instruments.
        # TODO(#1136): Remove skip once memory management is improved
        if sys.version_info.minor < 7:
            pytest.skip("skipping 3.6 for {:} ({:} =? {:})".format(
                inst_dict, inst_dict['inst_module'].__name__.find(
                    'pysat_testing'), len(inst_dict['inst_module'].__name__)
                - len('pysat_testing')))
            return

        # Update the Instrument dict with the desired pad
        if 'kwargs' in inst_dict.keys():
            inst_dict['kwargs']['pad'] = pad
        else:
            inst_dict['kwargs'] = {'pad': pad}

        # Assign the expected representation
        if type(pad) in [dict]:
            pad_repr = repr(pds.DateOffset(days=1))
        elif type(pad) in [dt.timedelta]:
            pad_repr = "1 day, 0:00:00"
        else:
            pad_repr = repr(pad)

        self.test_inst, self.date = initialize_test_inst_and_date(inst_dict)
        if len(self.test_inst.files.files) > 0:
            # Make sure the strict time flag doesn't interfere with
            # the load tests
            load_and_set_strict_time_flag(self.test_inst, self.date,
                                          raise_error=True, clean_off=True)

            if self.test_inst.empty:
                # This will be empty if this is a forecast file that doesn't
                # include the load date
                self.test_inst.pad = None
                load_and_set_strict_time_flag(self.test_inst, self.date,
                                              raise_error=True, clean_off=True)
                assert not self.test_inst.empty, \
                    "No data on {:}".format(self.date)
                assert self.test_inst.index.max() < self.date, \
                    "Padding should have left data and didn't"
            else:
                # Padding was successful, evaluate the data index length
                assert (self.test_inst.index[-1]
                        - self.test_inst.index[0]).total_seconds() < 86400.0

                # Evaluate the recorded pad
                inst_str = self.test_inst.__str__()
                assert inst_str.find(
                    'Data Padding: {:s}'.format(pad_repr)) > 0, "".join([
                        "bad pad value: ", pad_repr, " not in ", inst_str])
        else:
            pytest.skip("Download data not available")

        return

    @pytest.mark.download
    def test_remote_file_list(self, inst_dict):
        """Test if optional list_remote_files routine exists and is callable.

        Parameters
        ----------
        inst_dict : dict
            Dictionary containing info to instantiate a specific instrument.
            Set automatically from instruments['download'] when
            `initialize_test_package` is run.

        """

        self.test_inst, self.date = initialize_test_inst_and_date(inst_dict)
        name = '_'.join((self.test_inst.platform, self.test_inst.name))

        if hasattr(getattr(self.inst_loc, name), 'list_remote_files'):
            assert callable(self.test_inst.remote_file_list)

            # Check for username
            if 'user_info' in inst_dict.keys():
                dl_dict = inst_dict['user_info']
            else:
                dl_dict = {}

            files = self.test_inst.remote_file_list(start=self.date,
                                                    stop=self.date, **dl_dict)

            # If test date is correctly chosen, files should exist
            assert len(files) > 0
        else:
            pytest.skip("remote_file_list not available")

        return

    @pytest.mark.no_download
    def test_download_warning(self, inst_dict):
        """Test that instruments without download support have a warning.

        Parameters
        ----------
        inst_dict : dict
            Dictionary containing info to instantiate a specific instrument.
            Set automatically from instruments['no_download'] when
            `initialize_test_package` is run.

        """

        test_inst, self.date = initialize_test_inst_and_date(inst_dict)

        with warnings.catch_warnings(record=True) as war:
            test_inst.download(self.date, self.date)

        assert len(war) >= 1
        categories = [war[j].category for j in range(0, len(war))]
        assert UserWarning in categories
        return
