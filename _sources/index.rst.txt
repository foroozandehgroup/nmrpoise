POISE User Guide
================

POISE (*Parameter Optimisation by Iterative Spectral Evaluation*) is a Python package for on-the-fly optimisation of NMR parameters in Bruker's TopSpin software.

The code is licensed under `the GNU General Public License v3 <https://www.gnu.org/licenses/gpl-3.0.en.html>`_ and can be found on `GitHub <https://github.com/foroozandehgroup/nmrpoise>`_.

For more information, do check out the paper:

 - Yong, J. R. J.; Foroozandeh, M. On-the-Fly, Sample-Tailored Optimization of NMR Experiments. *Anal. Chem.* **2021,** *93* (31), 10735–10739. DOI: `10.1021/acs.analchem.1c01767 <https://doi.org/10.1021/acs.analchem.1c01767>`_.

.. note::

    The documentation you are currently reading is for version |version| of POISE.
    To check your current version of POISE, type ``poise --version`` in TopSpin.

    The most recent HTML version of the documentation can always be found at

        https://foroozandehgroup.github.io/nmrpoise.

    A PDF version can be found at

        https://foroozandehgroup.github.io/nmrpoise/poise.pdf


In here you will find guides on setting POISE up and using it in routine NMR applications.
This guide can largely be read in sequence.
However, depending on your level of interaction with the software, you may not need to read all of it.
For example, if somebody else has already set up POISE for you, you can probably skip to `running`.


.. toctree::
   :maxdepth: 2
   
   install
   routines
   running
   frontend
   automation
   costfunctions
   au
   customcf
   dev
