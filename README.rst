Ldtools
~~~~~~~

Ldtools is a simple library to handle RDF data in a convenient way.
It can be used as a simple ORM for Linked Data Resources and their Origins.
A resource "http://dbpedia.org/resource/Karlsruhe" might be mentioned by different origins.
Ldtools helps to keep track of verified statements (authoritative) about resources and provides an API to query more information about resources.

Different rdf triple storage backends are provided for the retrieved data: RestBackend, FileBackend or MemoryBackend

The CLI ldtools can be used to retrieve information about linked data resources.



Installation
------------

Just use pip:

    pip install Ldtools

This will install all dependencies (argparse, rdflib) needed and provide the command line utility "ldtools".

Alternatively, do a git clone and execute python setup.py install/develop.



How to use it?
==============

Via the commandline, all information within a Linked Data resource can be retrieved by executing

    ldtools http://dbpedia.org/resource/Karlsruhe

Further options can be utilised to influence whether the URIs that are discovered within the origin should be followed and how deep. Try

    ldtools --help

for more usage information.

Alternatively, the python console can be used:

First, we create an Origin object:

    import pprint, rdflib
    from ldtools.resource import Resource
    from ldtools.origin import Origin

    uri = "http://dbpedia.org/resource/Karlsruhe"
    origin, created = Origin.objects.get_or_create(uri)

Process it, hopefully discovering more Origins in there (rdfs:seeAlso, owl:sameAs...):

    origin.GET(only_follow_uris=[rdflib.OWL.sameAs,rdflib.RDFS.seeAlso])

If everything went well, there now is a Resource object for our uri:

    resource, created = Resource.objects.get_or_create(uri, origin=origin)
    pprint.pprint(resource.__dict__)

Process all the other Origins we know about

    Origin.objects.GET_all()

Result: 5 URIs crawled and 500 Resources discovered and processed.


Why?
----

* The Semantic Web is out there and there is really not enough tools yet to work with Linked Data
* SPARQL is not needed to get the RAW data from resources, this library demonstrates that. Just the basic Linked Data Stack: URIs, Content Negotiation, RDF needed
* ldtools intends to make it easy to handle the data you get from an URI and to follow links you discover
* Based on that, you can modify your objects and PUT them back to their origin


Contact
-------
You can contact me directly via Twitter @daniel_aus_wa or drop me an email to the address mentioned in setup.py

Please submit ideas and bugs to http://github.com/dmr/Ldtools/issues.


Tests
-----

To run the tests, install spec and/or nose and requests and run them:

    pip install spec unittest2
    nosetests

Thank you http://travis-ci.org for running the tests :)
[![Build Status](https://travis-ci.org/dmr/Ldtools.png)](https://travis-ci.org/dmr/Ldtools)


Credits
-------
Thanks to Django, Flask, peewee and sentry for inspiration regarding model structure!
