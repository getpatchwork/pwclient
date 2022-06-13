Configuration
=============

*pwclient* reads configuration from the ``.pwclientrc`` file, located in your
home directory (``$HOME`` or ``~``). You can point to another path with the
environment variable ``PWCLIENTRC``. Patchwork itself provides sample
``.pwclientrc`` files for projects at:

  /project/{projectName}/pwclientrc/

For example, `here`__ is the ``.pwclientrc`` file for Patchwork itself.

__ https://patchwork.ozlabs.org/project/patchwork/pwclientrc/


Format
------

The ``.pwclientrc`` file is an `INI-style`__ config file, **containing** an
``options`` section along with a section for each project.

The ``options`` section provides the following configuration options:

``default``
  The default project to use. Must be configured if not specifying a project
  via the command line.

``signoff``
  Add a ``Signed-Off-By:`` line to commit messages when applying patches using
  the :command:`git-am` command. Defaults to ``False``.

``3way``
  Enable three-way merge when applying patches using the :command:`git-am`
  command. Defaults to ``False``.

``msgid``
  Add a ``Message-Id:`` line to commit messages when applying patches using
  the :command:`git-am` command. Defaults to ``False``.

The names of the project sections must correspond to the project names in
Patchwork, as reflected in the project's URL in Patchwork. Multiple projects
can be defined, but no two projects can share the same name. Project sections
require the following configuration options:

``url``
  The URL of the API endpoint for the Patchwork instance that the project is
  available on. This depends on the API *backend* in use. For the ``rest``
  backend, this will typically be ``$PATCHWORK/api``. For example:

    https://patchwork.ozlabs.org/api

  For the ``xmlrpc`` backend, this is will typically be
  ``$PATCHWORK_URL/xmlrpc``. For example:

    https://patchwork.ozlabs.org/xmlrpc

In addition, the following options are optional:

``backend``
  The API backend to use. One of: ``rest``, ``xmlrpc``

``username``
  Your Patchwork username.

``password``
  Your Patchwork password.

``token``
  Your Patchwork API token. (only supported with ``rest`` backend)

.. note::

   Patchwork credentials are only needed for certain operations, such as
   updating the state of a patch. You will also require admin priviledges on
   the instance in question.

__ https://en.wikipedia.org/wiki/INI_file


Example
-------

::

    [options]
    default = patchwork

    [patchwork]
    backend = rest
    url = http://patchwork.ozlabs.org/api/
    token = 088cade25e52482e6486794ef4a4561d3e5fe727

Legacy Format
-------------

Older Patchwork instances may provide a legacy version of the ``.pwclientrc``
file that did not support multiple projects. *pwclient* will automatically
convert this version of the file to the latest version.
