Ldtools
~~~~~~~

Ldtools is a simple library to handle RDF data more conveniently..


Features
========

* A lightweight "ORM" to handle Linked Data Resources and their Origins
* Written in python
* Stores everything in memory
* Dependencies: rdflib
* API is still very unstable because I need to add more features and don't know yet how this will turn out
* 90% test coverage to describe how it works. Most functionality is described in the tests
* More features following soon.


How to use it?
==============

First, we create a Resource object (this will create an Origin object):

    from ldtools import Resource, Origin

    uri = "http://dbpedia.org/resource/Karlsruhe"

    r, created = Resource.objects.get_or_create(uri, auto_origin=True)


Process it, hopefully discovering more Origins in there (rdfs:seeAlso, owl:sameAs...)

    import rdflib

    r._origin.GET(only_follow_uris=[rdflib.OWL.sameAs])


    import pprint
    
    pprint.pprint(r.__dict__)


Process all the other Origins we know about

    Origin.objects.GET_all()


Result: 5 URIs crawled and 500 Resources discovered!


Why?
----

* The Semantic Web is out there and there is really not enough tools yet to work with Linked Data.
* SPARQL is not needed to get the RAW data from resources, this library demonstrates that. Just the basic Linked Data Stack: URIs, Content Negotiation, RDF needed.
* ldtools intends to make it easy to handle the data you get from an URI: read what's in there, follow links you discover
* Modification of objects and ability to write back to its origin will follow.


Contact
-------
You can contact me directly via Twitter @daniel_aus_wa or drop me an email to the address mentioned in setup.py

Please submit ideas and bugs to http://github.com/dmr/ldtools/issues.


Credits
-------
Thanks to Django, Flask and django-sentry for inspiration regarding model structure!