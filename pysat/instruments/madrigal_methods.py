# -*- coding: utf-8 -*-.
"""Provides default routines for integrating CEDAR Madrigal instruments into
pysat, reducing the amount of user intervention.

 """

from __future__ import print_function
from __future__ import absolute_import

import sys
import pandas as pds
import pysat

def cedar_rules():
    """ General acknowledgement statement for Madrigal data

    Returns
    -------
    ackn : string
        String with general acknowledgement for all CEDAR Madrigal data

    """

    ackn = "Contact the PI when using this data, in accordance with the CEDAR"
    ackn += " 'Rules of the Road'"
    return ackn
                         
# support load routine
def load(fnames, tag=None, sat_id=None, xarray_coords=[]):
    """Loads data from Madrigal into Pandas.
    
    This routine is called as needed by pysat. It is not intended
    for direct user interaction.
    
    Parameters
    ----------
    fnames : array-like
        iterable of filename strings, full path, to data files to be loaded.
        This input is nominally provided by pysat itself.
    tag : string ('')
        tag name used to identify particular data set to be loaded.
        This input is nominally provided by pysat itself. While
        tag defaults to None here, pysat provides '' as the default
        tag unless specified by user at Instrument instantiation.
    sat_id : string ('')
        Satellite ID used to identify particular data set to be loaded.
        This input is nominally provided by pysat itself.
    xarray_coords : list
        List of keywords to use as coordinates if xarray output is desired
        instead of a Pandas DataFrame (default=[])
    
    Returns
    -------
    data : pds.DataFrame or xr.DataSet
        A pandas DataFrame or xarray DataSet holding the data from the HDF5 file
    metadata : pysat.Meta
        Metadata from the HDF5 file, as well as default values from pysat

    Examples
    --------
    ::
        inst = pysat.Instrument('jro', 'isr', 'drifts')
        inst.load(2010,18)

    """    
    import h5py
    import numpy as np

    # Ensure 'time' wasn't included as a coordinate, since it is the default
    if 'time' in xarray_coords:
        xarray_coords.pop(xarray_coords.index('time'))

    # Open the specified file
    filed = h5py.File(fnames[0], 'r')
    # data
    file_data = filed['Data']['Table Layout']
    # metadata
    file_meta = filed['Metadata']['Data Parameters']
    # load up what is offered into pysat.Meta
    meta = pysat.Meta()
    meta.info = {'acknowledgements':"See 'meta.Experiment_Notes' for " +
                 "instrument specific acknowledgements\n" + cedar_rules(),
                 'references':"See 'meta.Experiment_Notes' for references"}
    labels = []
    for item in file_meta:
        # handle difference in string output between python 2 and 3
        name_string = item[0]
        unit_string = item[3]
        desc_string = item[1]
        if sys.version_info[0] >= 3:
            name_string = name_string.decode('UTF-8')
            unit_string = unit_string.decode('UTF-8')
            desc_string = desc_string.decode('UTF-8')
        labels.append(name_string)
        meta[name_string.lower()] = {'long_name':name_string,
                                     'units':unit_string,
                                     'desc':desc_string}

    # add additional metadata notes
    # custom attributes attached to meta are attached to
    # corresponding Instrument object when pysat receives
    # data and meta from this routine
    for key in filed['Metadata']:
        if key != 'Data Parameters':
            setattr(meta, key.replace(' ', '_'), filed['Metadata'][key][:])
    # data into frame, with labels from metadata
    data = pds.DataFrame.from_records(file_data, columns=labels)
    # lowercase variable names
    data.columns = [item.lower() for item in data.columns]
    # datetime index from times
    time_keys = np.array(['year', 'month', 'day', 'hour', 'min', 'sec'])
    if not np.all([key in data.columns for key in time_keys]):
        time_keys = [key for key in time_keys if key not in data.columns]
        raise ValueError("unable to construct time index, missing " +
                         "{:}".format(time_keys))
    
    time = pysat.utils.create_datetime_index(year=data.loc[:,'year'],
                                             month=data.loc[:,'month'],
                                             day=data.loc[:,'day'],
                                             uts=3600.0 * data.loc[:,'hour'] +
                                             60.0 * data.loc[:,'min'] +
                                             data.loc[:,'sec'])
    # Declare index or recast as xarray
    if len(xarray_coords) > 0:
        if not np.all([xkey.lower() in data.columns for xkey in xarray_coords]):
            estr = 'unknown coordinate key in {:}, '.format(xarray_coords)
            estr += 'use only {:}'.format(data.columns)
            raise ValueError(estr)

        # Append time to the data frame and add as the first coordinate
        data = data.assign(time=pds.Series(time, index=data.index))
        xarray_coords.insert(0, 'time')

        # Set the indices
        data = data.set_index(xarray_coords)

        # Recast the data as an xarray
        data = data.to_xarray()
    else:
        # Set the index to time, and put up a warning if there are duplicate
        # times.  This could mean the data should be stored as an xarray DataSet
        data.index = time

        if np.any(time.duplicated()):
            print("WARNING: duplicated time indices, consider specifing " +
                  "additional coordinates and storing the data as an xarray" +
                  " DataSet")

    return data, meta


def download(date_array, inst_code=None, kindat=None, data_path=None, user=None,
             password=None, url="http://cedar.openmadrigal.org",
             file_format='hdf5'):
    """Downloads data from Madrigal.
    
    Parameters
    ----------
    date_array : array-like
        list of datetimes to download data for. The sequence of dates need not
        be contiguous.
    inst_code : string (None)
        Madrigal instrument code(s), cast as a string.  If multiple are used,
        separate them with commas.
    kindat : string  (None)
        Experiment instrument code(s), cast as a string.  If multiple are used,
        separate them with commas.
    data_path : string (None)
        Path to directory to download data to.
    user : string (None)
        User string input used for download. Provided by user and passed via
        pysat. If an account
        is required for dowloads this routine here must error if user not
        supplied.
    password : string (None)
        Password for data download.
    url : string ('http://cedar.openmadrigal.org')
        URL for Madrigal site
    file_format : string ('hdf5')
        File format for Madrigal data.  Load routines currently only accept
        'hdf5', but any of the Madrigal options may be used here.

    Returns
    --------
    Void : (NoneType)
        Downloads data to disk.
    
    Notes
    -----
    The user's names should be provided in field user. Ruby Payne-Scott should
    be entered as Ruby+Payne-Scott
    
    The password field should be the user's email address. These parameters
    are passed to Madrigal when downloading.
    
    The affiliation field is set to pysat to enable tracking of pysat downloads.
    
    """
  
    import subprocess

    if inst_code is None:
        raise ValueError("Must supply Madrigal instrument code")

    if kindat is None:
        raise ValueError("Must supply Madrigal experiment code")

    # currently passes things along if no user and password supplied
    # need to do this for testing
    # TODO, implement user and password values in test code
    # specific to each instrument
    if user is None:
        print ('No user information supplied for download.')
        user = 'pysat_testing'
    if password is None:
        print ('Please provide email address in password field.')
        password = 'pysat_testing@not_real_email.org'

    try:
        a = subprocess.check_output(["globalDownload.py", "--verbose", 
                                     "--url="+url, '--outputDir='+data_path,
                                     '--user_fullname='+user,
                                     '--user_email='+password,
                                     '--user_affiliation=pysat',
                                     '--format='+file_format, \
                            '--startDate='+date_array[0].strftime('%m/%d/%Y'),\
                            '--endDate='+date_array[-1].strftime('%m/%d/%Y'),
                                     '--inst='+inst_code, '--kindat='+kindat])
        print ('Feedback from openMadrigal ', a)
    except OSError as err:
        print("problem running globalDownload.py, check python path")