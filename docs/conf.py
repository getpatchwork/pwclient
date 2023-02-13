# -*- coding: utf-8 -*-
#
# pwclient documentation build configuration file

try:
    import furo  # noqa

    has_furo_theme = True
except ImportError:
    has_furo_theme = False

# -- General configuration ------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'reno.sphinxext',
    'sphinxcontrib.autoprogram',
]

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'pwclient'
copyright = '2018-present, Stephen Finucane'
author = 'Stephen Finucane'

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
if has_furo_theme:
    html_theme = 'furo'
