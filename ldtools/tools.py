from ldtools.origin import Origin
from ldtools.resource import Resource
from ldtools.utils import get_slash_url, get_rdflib_uriref


def get_authoritative_resource(uri, create_nonexistent_origin=True):
    """Tries to return the Resource object from the authoritative origin uri"""

    uri = get_rdflib_uriref(uri)
    origin_uri = get_slash_url(uri)

    authoritative_origin = Origin.objects.filter(uri=origin_uri)
    authoritative_origin_list = list(authoritative_origin)
    if len(authoritative_origin_list) == 1:
        origin = authoritative_origin_list[0]
    else:
        if create_nonexistent_origin:
            origin, created = Origin.objects.get_or_create(uri=origin_uri)
        else:
            raise Resource.DoesNotExist(
                "No authoritative Resource found for %s" % uri)

    if not origin.has_unsaved_changes():
        origin.GET(only_follow_uris=[], raise_errors=False)

    authoritative_resource = Resource.objects.get(uri=uri, origin=origin)
    return authoritative_resource
