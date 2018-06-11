========
pwclient
========

.. NOTE: If editing this, be sure to update the line numbers in 'doc/index'

.. image:: https://badge.fury.io/py/pwclient.svg
   :target: https://badge.fury.io/py/pwclient
   :alt: PyPi Status

.. image:: https://readthedocs.org/projects/pwclient/badge/?version=latest
   :target: https://pwclient.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

*pwclient* is a VCS-agnostic tool for interacting with `Patchwork`__, the
web-based patch tracking system.

__ http://jk.ozlabs.org/projects/patchwork/


Installation
------------

The easiest way to install *pwclient* and its dependencies is using ``pip``. To
do so, run:

.. code-block:: bash

   $ pip install pwclient

You can also install *pwclient* manually. First, install the required
dependencies. On Fedora, run:

.. code-block:: bash

   $ sudo dnf install python-pbr

On Ubuntu, run:

.. code-block:: bash

   $ sudo apt-get install python-pbr

Once dependencies are installed, clone this repo and run ``setup.py``:

.. code-block:: bash

   $ git clone https://github.com/getpatchwork/pwclient
   $ cd pwclient
   $ pip install --user .  # or 'sudo python setup.py install'

Getting Started
---------------

To use *pwclient*, you will need a ``.pwclientrc`` file, located in your home
directory (``$HOME`` or ``~``). Patchwork itself provides sample
``.pwclientrc`` files for projects at ``/project/{projectName}/pwclientrc/``.
For example, `here`__ is the ``.pwclientrc`` file for Patchwork itself.

__ https://patchwork.ozlabs.org/project/patchwork/pwclientrc/


Development
-----------

If you're interested in contributing to *pwclient*, first clone the repo:

.. code-block:: bash

   $ git clone https://github.com/getpatchwork/pwclient
   $ cd pwclient

Create a *virtualenv*, then install the package in `editable`__ mode:

.. code-block:: bash

   $ virtualenv .venv
   $ source .venv/bin/activate
   $ pip install --editable .

__ https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs


Documentation
-------------

Documentation is available on `Read the Docs`__

__ https://pwclient.readthedocs.io/
