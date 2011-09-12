# -*- coding: utf-8 -*-
__version__ = "0.5.3"
__useragent__ = ('ldtools-%s (http://github.com/dmr/ldtools, daniel@nwebs.de)'
                 % __version__)

import datetime
import logging
import mimetypes
import os
import rdflib
import shutil
import urllib2
import glob

# add n3 to known mimetypes
mimetypes.add_type("text/n3", ".n3")

logger = logging.getLogger("ldtools")


def get_file_extension(filename):
    """
    >>> get_file_extension("test.xml")
    'xml'
    >>> get_file_extension("test.1234123.xml")
    'xml'
    >>> get_file_extension("test")
    ''
    """
    extension = filename.split(".")[1:][-1:]
    return str(extension[0]) if extension else ""


def assure_parser_plugin_exists(format):
    # TODO: double check if parser for format exists -->
    # TODO: move parser to backend
    try:
        rdflib.graph.plugin.get(name=format,
                                kind=rdflib.parser.Parser)
        return True
    except rdflib.plugin.PluginException as e:
        logger.error("Parser does not exist for format %s" % format)
        return False


def guess_format_from_filename(file_name):
    file_extension = file_name.split(".")[-1]
    if file_name != file_extension:
        return file_extension


class AbstractBackend(object):
    """Abstract Backend. Overwrite in subclasses"""
    def GET(self, uri): raise NotImplementedError
    def PUT(self): raise NotImplementedError


class RestBackend(AbstractBackend):

    def GET(self, uri):
        """lookup URI"""
        # TODO: do friendly crawling: use robots.txt speed
        # limitation definitions

        if not hasattr(self, "uri"):
            self.uri = uri
        else:
            if not self.uri == uri:
                raise Exception("You cannot pass different uris to the same "
                                "backend")

        headers = {'User-agent': __useragent__,
                   'Accept':('text/n3;q=1,'
                             'application/rdf+xml,text/rdf+n3;q=0.9,'
                             'application/xhtml+xml;q=0.5, */*;q=0.1')}

        request = urllib2.Request(url=self.uri, headers=headers)

        opener = urllib2.build_opener() #SmartRedirectHandler())
        result_file = opener.open(request)

        self.content_type = result_file.headers['Content-Type'].split(";")[0]

        # Many servers don't do content negotiation: if one of the following
        # content_types are returned by server, assume the mapped type
        content_type_mapping = {
            "text/plain": "application/rdf+xml"
        }

        if self.content_type in content_type_mapping:
            self.content_type = content_type_mapping[self.content_type]

        file_extension = mimetypes.guess_extension(self.content_type)
        if file_extension:
            format = file_extension.strip(".")
            if format in ["rdf", "ksh"]:
                # fix responses that we know are wrong
                format = "xml"

            # TODO: try rdfa for format = "html"?

            if assure_parser_plugin_exists(format):
                self.format = format

                data = result_file.read()

                return data
        else:
            #logger.warning("%s not supported by ldtools. Trying 'xml'..."
            #               % result_file.headers['Content-Type'])
            #self.format = "xml"
            #self.content_type = mimetypes.types_map[".%s" % self.format]
            # TODO: assumption here: empty string will not cause harm because
            # Origin.GET() will break after this
            return

    def PUT(self, data):
        assert self.uri, "GET has to be called before PUT possible"

        # TODO: authentication? oauth?
        #h = httplib2.Http()
        #h.add_credentials('name', 'password')
        #resp, content = h.request(uri, "PUT", body=data, headers=headers)
        #if resp.status != 200: raise Error(resp.status, errmsg, headers)
        #return resp, content
        headers={"content-type": self.content_type,
                 "User-Agent": __useragent__,
                 "Content-Length": str(len(data))}

        opener = urllib2.build_opener(urllib2.HTTPHandler)
        request = urllib2.Request(self.uri,
                                  data=data,
                                  headers=headers)
        request.get_method = lambda: 'PUT'
        response = opener.open(request)
        # assert status_code 200, 201?


class FileBackend(AbstractBackend):
    """Manages one xml file --> Uri that the user wants to "PUT" to is not
    flexible!
    """

    def __init__(self, filename, format=None):
        assert os.path.exists(filename)

        format = format if format else guess_format_from_filename(filename)
        if assure_parser_plugin_exists(format):
            self.format = format
        else:
            logger.error("No format set!")

        self.filename = filename

    def GET(self, uri):
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
        assert self.uri, "GET has to be called before PUT possible"

        if os.path.exists(self.filename):
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
            shutil.copy(self.filename, old_version)

        with open(self.filename, "w") as f:
            f.write(data)
        self.old_version = old_version

    def revert_to_old_version(self):
        if hasattr(self, "old_version"):
            logger.info("Reverting to version before last saved version")
            shutil.copy(self.old_version, self.filename)
            os.remove(self.old_version)
            delattr(self, "old_version")


class MemoryBackend(AbstractBackend):
    def __init__(self, data=None, format="xml"):
        self.data = data if data else ""
        self.format = format

    def GET(self, uri):
        return self.data

    def PUT(self, data):
        self.data = data
