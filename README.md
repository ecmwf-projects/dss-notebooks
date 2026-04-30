# dss-notebooks

This library of notebooks for documenting various aspects of the ECMWF Data Stores Service (DSS).
This includes the accessing and visualising the datasets available via the DSS, and providing
traceability and documentation for computational components of the service.

## datasets/

This folder contains notebooks which are relevent to specific datasets. The notebooks provided here
provide simple demonstrations of accessing and visualising the data available on the CDS
with earthkit, in the demo.ipynb notebooks.

Where available, demonstrations of how to access the Analysis Ready Cloud Optimised (ARCO) data
using xarray and earthkit tools. For more details on the ARCO data made available via the
ECMWF-DSS, please refer to the
[ARCO data documentation pages](https://confluence.ecmwf.int/x/8aYZJg).

Additionally the dataset/dss-jupyter-forms.ipynb notebook which provides an interactive access to the 
entire DSS catalogue from an integrated webform.

## documentation/

This folder contains notebooks which help explain various backend processes that are done by the CADS
(for example the GRIB to NetCDF conversion), and/or to advise users on how to do certain computations
(for example, how to compute the daily accumulation of the ERA5-land variables). Generally, these notebooks
are referenced and embeded in more user friendly documentation pages, but feel free to explore here.

