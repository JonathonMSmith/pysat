# -*- coding: utf-8 -*-
#
"""Configuration file that builds the pysat documentation.

This file is execfile()d with the current directory set to its containing dir.

Note
----
Not all possible configuration values are present in this autogenerated file.

"""

import json
import os
import sys

import pysat

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
# sys.path.insert(0, os.path.abspath('.'))

sys.path.insert(0, os.path.abspath('..'))
pysat.params['data_dirs'] = '.'


# added by RS, trying to get __init__ method documented
autoclass_content = 'both'
# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.todo',
    'sphinx.ext.imgmath',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'numpydoc',
    'IPython.sphinxext.ipython_console_highlighting',
    'm2r2'
]

# added by RS
numpydoc_show_class_members = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
source_suffix = '.rst'

# The encoding of source files.
# source_encoding = 'utf-8-sig'

# The main toctree document (using required variable name).
master_doc = 'index'

# General information about the project.
zenodo = json.loads(open('../.zenodo.json').read())
project = 'pysat'
author = ', '.join([x['name'] for x in zenodo['creators']])
copyright = ', '.join(['2021', author])
title = '{:s} Documentation'.format(project)
description = 'Supports science analysis across disparate data platforms'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = pysat.__version__[::-1].partition('.')[2][::-1]
# The full version, including alpha/beta/rc tags.
release = pysat.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = 'en'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['.build', '.dist']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinx_rtd_theme'
html_theme_path = ["_themes", ]
html_logo = os.path.join(os.path.abspath('.'), 'images', 'logo.png')
html_theme_options = {'logo_only': True}

# Output file base name for HTML help builder.
htmlhelp_basename = '{:s}doc'.format(project)

# -- Options for LaTeX output ---------------------------------------------

# The paper size ('letterpaper' or 'a4paper').
# 'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
# 'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
# 'preamble': '',

# Latex figure (float) alignment
# 'figure_align': 'htbp',
latex_elements = {}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [(master_doc, '{:s}.tex'.format(project), title, author,
                    'manual')]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
latex_logo = './images/logo.png'

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
# latex_use_parts = False

# If true, show page references after internal links.
# latex_show_pagerefs = False

# If true, show URL addresses after external links.
# latex_show_urls = False

# Documents to append as an appendix to all manuals.
# latex_appendices = []

# If false, no module index is generated.
# latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [(master_doc, project, title, [author], 1)]

# If true, show URL addresses after external links.
# man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [(master_doc, project, title, author, project,
                      description, 'Space Physics')]

# -- Options for Epub output ----------------------------------------------

# Bibliographic Dublin Core info.
epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright

# -- Options for Intersphinx connection -----------------------------------

intersphinx_mapping = {'portalocker':
                       ('https://portalocker.readthedocs.io/en/latest',
                        None)}
