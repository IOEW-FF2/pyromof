# Pryomof
Pyromof is an oemof-based optimization model of a single pyrolysis plant with flexibility options. It is being developed within the project [PyFlex](https://www.ioew.de/projekt/pyflex_pyrolysetechnologie_als_intersektorale_flexibilitaetsmassnahme_im_energiesystem_deutschland).

To install is, you must have Python installed (ideally Python3.12, but other versions do probably also work). You can then clone the github repository and install it with `pip install -e .`. The `-e`-flag installs the project in editable mode - if you only want to run the model, you can install it without it.
In order to run the model you need a solver. By default, the code expects the solver cbc. If you want to use a different one, you have to adjust the code in pyromof/optimize.py.

If you want to contribute to this project, you also need to install git, flake8, pytest and black.