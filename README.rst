ldtools
=======

* A lightweight "ORM" to handle Linked Data Resources and their Origins
* Written in python
* Stores everything in memory
* Dependencies: rdflib
* API is still very unstable because I need to add more features and don't know yet how this will turn out
* 90% test coverage to describe how it works


How to use it?
--------------

    # Most functionality is describes in the tests. I'll try to describe the
    # basic ideas here soon.

    from ldtools import Resource, Origin
    import rdflib

    # First, we define the Resource object and thereby its Origin object
    uri = "http://dbpedia.org/resource/Karlsruhe"
    r, created = Resource.objects.get_or_create(uri, auto_origin=True)

    # Process it, hopefully discovering more Origins in there (rdfs:seeAlso, owl:sameAs...)
    # process it
    r._origin.GET(GRAPH_SIZE_LIMIT=25000, follow_uris=[rdflib.RDFS.seeAlso,rdflib.OWL.sameAs], handle_owl_imports=True)

    assert Resource.objects.all() > 1
    assert Origin.objects.all() > 1

    # process all the other Origins we found
    Origin.objects.GET_all()

    import pprint
    pprint.pprint(r.__dict__)

    print "Crawled %s Origins and collected %s Resources" % (len(list(Origin.objects.filter(processed=True))), len(list(Resource.objects.all())))


Why?
----

* The Semantic Web is out there and there is really not enough tools yet to work with Linked Data.
* SPARQL is not needed to get the RAW data from resources, this library demonstrates that. Just the basic Linked Data Stack: URIs, Content Negotiation, RDF needed.
* ldtools intends to make it easy to handle the data you get from an URI: read what's in there, follow links you discover
* Modification of objects and ability to write back to its origin will follow.


Contact
=======
You can contact me directly via Twitter @daniel_aus_wa or drop me an email to the address mentioned in setup.py

Please submit ideas and bugs to http://github.com/dmr/ldtools/issues.


Credits
-------
Thanks to Django, Flask and django-sentry for inspiration regarding model structure!