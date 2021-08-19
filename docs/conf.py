#  Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('../nmrpoise'))

# Get version number
exec(open('../nmrpoise/_version.py').read())

# -- Project information -----------------------------------------------------

project = 'poise'
copyright = '2021, Jonathan Yong & Mohammadali Foroozandeh'
author = 'Jonathan Yong & Mohammadali Foroozandeh'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "numpydoc",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable/", None),
}

rst_prolog = """
.. |version| replace:: {}
.. |Path| replace:: :class:`Path <pathlib.Path>`
.. |ndarray| replace:: :class:`ndarray <numpy.ndarray>`
.. |v| replace:: |br| |vspace|
.. |br| raw:: html

   <br />

.. |vspace| raw:: latex

   \\vspace{{5mm}}
""".format(__version__)

default_role = "any"

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_templates']

html_theme_options = {
    "page_width": "1000px",
    "sidebar_width": "250px",
}

html_sidebars = {
    '**': [
        'about.html',
        'sidebar_links.html',
        'navigation.html',
        'relations.html',
        'searchbox.html',
        'donate.html',
    ]
}

html_scaled_image_link = False

# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    "fontpkg": "",
    "fncychap": "",
    "preamble": r"""
        \setkeys{Gin}{width=0.6\linewidth}
        \usepackage{charter}
        \usepackage[defaultsans]{lato}
        \usepackage{inconsolata}
        """,
    "extraclassoptions": "openany",
    "printindex": "\\def\\twocolumn[#1]{#1}\\printindex",
}
