# -*- coding: utf-8 -*-
#
# pwclient documentation build configuration file

try:
    import sphinx_rtd_theme  # noqa
    has_rtd_theme = True
except ImportError:
    has_rtd_theme = False

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
needs_sphinx = '1.5'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'reno.sphinxext',
    'sphinxcontrib.autoprogram',
]

# The master toctree document.
master_doc = 'contents'

# General information about the project.
project = u'pwclient'
copyright = u'2018, Stephen Finucane'
author = u'Stephen Finucane'

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
if has_rtd_theme:
    html_theme = 'sphinx_rtd_theme'
