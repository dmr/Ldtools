Ldtools
~~~~~~~

Ldtools is a simple library to handle RDF data more conveniently.


Features
========

* A lightweight "ORM" to handle Linked Data Resources and their Origins
* Written in python
* Dependencies: rdflib
* Stores everything in memory
* API is still subject to change
* Tests describe basic functionality


How to use it?
==============

First, we create an Origin object:

    import pprint
    import rdflib
    from ldtools import Resource, Origin

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

Please submit ideas and bugs to http://github.com/dmr/ldtools/issues.


Credits
-------
Thanks to Django, Flask and django-sentry for inspiration regarding model structure!