# Patchwork command line client
# Copyright (C) 2022 Stephen Finucane <stephen@that.guru>
#
# SPDX-License-Identifier: GPL-2.0-or-later

# TODO(stephenfin): Simplyify this when we drop support for Python 3.7
try:
    import importlib.metadata as importlib_metadata
except ImportError:
    import importlib_metadata as importlib_metadata

try:
    __version__ = importlib_metadata.version(__package__ or __name__)
except importlib_metadata.PackageNotFoundError:
    __version__ = '0.0.0'
