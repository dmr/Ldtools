# -*- coding: utf-8 -*-
from ldtools import __version__, url, author_email

import datetime
import logging
import mimetypes
import os
import shutil
import socket
import rdflib

from ldtools.utils import urllib2

# set socket timeout. URLError will occur if time passed
socket.setdefaulttimeout(5)

__useragent__ = 'ldtools-{version} ({url}, {author_email})'.format(
    version=__version__, url=url, author_email=author_email
)

# add mimetypes python does not know yet
mimetypes.add_type("text/n3", ".n3")
mimetypes.add_type("text/rdf+n3", ".n3")
mimetypes.add_type("text/turtle", ".n3")


class FiletypeMappingError(Exception):
    pass


class ContentNegotiationError(Exception):
    pass


logger = logging.getLogger("ldtools")


def get_file_extension(filename):
    extension = filename.split(".")[1:][-1:]
    return str(extension[0]) if extension else ""


def assure_parser_plugin_exists(format):
    try:
        rdflib.graph.plugin.get(name=format, kind=rdflib.parser.Parser)
    except rdflib.plugin.PluginException:
        msg = "No parser plugin found for %s" % format
        logger.error(msg)
        raise ContentNegotiationError(msg)


def guess_format_from_filename(file_name):
    file_extension = file_name.split(".")[-1]
    if file_name != file_extension:
        return file_extension


class AbstractBackend(object):
    """Abstract Backend. Overwrite in subclasses"""
    pass


class RestBackend(AbstractBackend):
    GET_headers = {
        'User-agent': __useragent__,
        'Accept': (
            'text/n3,'
            'text/rdf+n3,'
            'application/rdf+xml;q=0.8'
            "text/turtle;q=0.7,"
            # 'application/xhtml+xml;q=0.5'
            # '*/*;q=0.1'
            # XHTML+RDFa
        )
    }

    PUT_headers = {"User-Agent": __useragent__}

    def GET(
        self,
        uri,
        extra_headers=None,
        httphandler=None,
    ):
        """Lookup URI and follow redirects. Return data"""

        if not hasattr(self, "uri"):
            self.uri = uri
        else:
            if not self.uri == uri:
                raise Exception("You cannot pass different uris to the same "
                                "backend")

        if httphandler:
            if isinstance(httphandler, list):
                opener = urllib2.build_opener(*httphandler)
            else:
                opener = urllib2.build_opener(httphandler)
        else:
            opener = urllib2.build_opener()

        if extra_headers:
            self.GET_headers.update(extra_headers)

        reference_time = datetime.datetime.now()

        request = urllib2.Request(url=uri, headers=self.GET_headers)

        try:
            resultF = opener.open(request)
        except (UnicodeEncodeError, socket.timeout):
            return None

        now = datetime.datetime.now()
        self.lookup_time = now - reference_time

        if resultF.geturl() != uri:
            logger.info(
                "%s was redirected. Content url: %r" % (
                    uri, resultF.geturl()))

        if "Content-Length" in resultF.headers:
            logger.info(
                "Content-Length: %s" % resultF.headers["Content-Length"])

        if "Content-Type" not in resultF.headers:
            raise FiletypeMappingError("No Content-Type specified in response")
        self.content_type = resultF.headers['Content-Type'].split(";")[0]

        # Many servers don't do content negotiation: if one of the following
        # content_types are returned by server, assume the mapped type
        overwrite_content_type_map = {
            "text/plain": "application/rdf+xml",
        }

        if self.content_type in overwrite_content_type_map:
            self.content_type = overwrite_content_type_map[self.content_type]

        try:
            file_extension = mimetypes.guess_extension(self.content_type)
            assert file_extension
        except AssertionError:
            logger.error(
                "{} not supported by ldtools".format(
                    resultF.headers['Content-Type']))
            raise FiletypeMappingError(
                "No mimetype found for %s" % self.content_type)

        format = file_extension.strip(".")

        # assure format is correct
        if format in ["rdf", "ksh"]:
            format = "xml"
        # check if rdflib parser exists for format
        assure_parser_plugin_exists(format)

        self.format = format
        return resultF.read()

    def PUT(self, data):
        assert self.uri, "GET has to be called before PUT possible"

        self.PUT_headers.update({
            "Content-Type": self.content_type,
            "Content-Length": str(len(data)),
        })

        opener = urllib2.build_opener(urllib2.HTTPHandler)
        request = urllib2.Request(self.uri,
                                  data=data,
                                  headers=self.PUT_headers)
        request.get_method = lambda: 'PUT'
        response = opener.open(request)
        return response


class FileBackend(AbstractBackend):
    """Manages one xml file as a data basis"""

    def __init__(self, filename,
                 format=None,
                 store_old_versions=True):
        assert os.path.exists(filename)

        format = format if format else guess_format_from_filename(filename)
        assure_parser_plugin_exists(format)

        self.format = format
        self.filename = filename
        self.store_old_versions = store_old_versions

    def GET(self,
            uri,
            extra_headers=None,
            httphandler=None,
            ):
        assert not extra_headers, "Not Implemented"
        assert not httphandler, "Not Implemented"
        if not hasattr(self, "uri"):
            self.uri = uri
        else:
            if not self.uri == uri:
                raise Exception("You cannot pass different uris to the same "
                                "backend")

        with open(self.filename, "r") as f:
            data = f.read()
        return data

    def PUT(self, data):
        assert self.uri, "GET has to be called before PUT"

        if os.path.exists(self.filename) and self.store_old_versions:
            # File already exists. Make backup copy
            now = datetime.datetime.strftime(datetime.datetime.utcnow(),
                                             '%Y%m%d-%H%M%S')
            file_extension = get_file_extension(self.filename)
            if file_extension:
                old_version = u"%s.%s.%s" % (
                    self.filename.strip(file_extension),
                    now, file_extension)
            else:
                old_version = u"%s_%s" % (self.filename, now)
            self.old_version = old_version
            shutil.copy(self.filename, old_version)

        with open(self.filename, "w") as f:
            f.write(data)

    def revert_to_old_version(self):
        assert self.store_old_versions, (
            "This FileBackend is not configured to store old versions")
        if hasattr(self, "old_version"):
            logger.info("Reverting to version before last saved version")
            shutil.copy(self.old_version, self.filename)
            os.remove(self.old_version)
            delattr(self, "old_version")


class MemoryBackend(AbstractBackend):
    def __init__(self, data=None, format="xml"):
        self.data = data if data else ""
        assure_parser_plugin_exists(format)
        self.format = format

    def GET(self,
            uri,
            extra_headers=None,
            httphandler=None,
            ):
        assert not extra_headers, "Not Implemented"
        assert not httphandler, "Not Implemented"
        return self.data

    def PUT(self, data):
        self.data = data
