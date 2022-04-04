# Patchwork command line client
# Copyright (C) 2018 Stephen Finucane <stephen@that.guru>
# Copyright (C) 2008 Nate Case <ncase@xes-inc.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import xmlrpc.client as xmlrpclib


class Transport(xmlrpclib.SafeTransport):
    def __init__(self, url):
        xmlrpclib.SafeTransport.__init__(self)
        self.credentials = None
        self.host = None
        self.proxy = None
        self.scheme = url.split('://', 1)[0]
        self.https = url.startswith('https')
        if self.https:
            self.proxy = os.environ.get('https_proxy')
        else:
            self.proxy = os.environ.get('http_proxy')
        if self.proxy:
            self.https = self.proxy.startswith('https')

    def set_credentials(self, username=None, password=None):
        self.credentials = '%s:%s' % (username, password)

    def make_connection(self, host):
        self.host = host
        if self.proxy:
            host = self.proxy.split('://', 1)[-1].rstrip('/')
        if self.credentials:
            host = '@'.join([self.credentials, host])
        if self.https:
            return xmlrpclib.SafeTransport.make_connection(self, host)
        else:
            return xmlrpclib.Transport.make_connection(self, host)

    def send_request(self, host, handler, request_body, debug):
        handler = '%s://%s%s' % (self.scheme, host, handler)
        return xmlrpclib.Transport.send_request(
            self,
            host,
            handler,
            request_body,
            debug,
        )
