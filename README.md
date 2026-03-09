# Pryomof
Pyromof is an [oemof.solph](https://oemof-solph.readthedocs.io/en/stable/index.html)-based optimization model of a single pyrolysis plant with flexibility options. It is being developed within the project [PyFlex](https://www.ioew.de/projekt/pyflex_pyrolysetechnologie_als_intersektorale_flexibilitaetsmassnahme_im_energiesystem_deutschland).

To install is, you must have Python installed (ideally Python3.12, but other versions do probably also work). You can then clone the github repository (`git clone https://github.com/IOEW-FF2/pyromof.git`), enter the folder and install it with `pip install -e .`. The `-e`-flag installs the project in editable mode - if you only want to run the model, you can install it without it.
In order to run the model you need a solver. By default, the code expects the solver cbc which you can find in https://github.com/coin-or/Cbc/releases. If you want to use a different one, you have to adjust the code in pyromof/optimize.py. If you use Windows, the file "cbc.exe" (located in the bin folder) should be placed in the same folder as this readme-file.
The input data are not provided within this repository. A description on how to design the input data and how to run the model is provided in docs/usage.md.

If you want to contribute to this project, you also need to install git, flake8, pytest and black.