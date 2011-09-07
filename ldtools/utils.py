import rdflib
from rdflib import compare
import logging

logger = logging.getLogger("ldtools")


def my_graph_diff(graph1, graph2):
    """Compares graph2 to graph1 and highlights everything that changed.
    Colored if pygments available"""

    import difflib

    # quick fix for wrong type
    if not type(graph1) == type(graph2) == rdflib.Graph:
        if type(graph1) == rdflib.ConjunctiveGraph:
            g1contexts = list(graph1.contexts())
            assert len(g1contexts) == 1
            graph1 = g1contexts[0]
        if type(graph2) == rdflib.ConjunctiveGraph:
            g2contexts = list(graph2.contexts())
            assert len(g2contexts) == 1
            graph2 = g2contexts[0]


    # Return if both graphs are isomorphic
    iso1 = compare.to_isomorphic(graph1)
    iso2 = compare.to_isomorphic(graph2)

    if graph1.identifier == graph2.identifier:
        str_bit = u"The 2 '%s' Graphs" % graph1.identifier
    else:
        str_bit = (u"Graphs '%s' and '%s'"
                   % (graph1.identifier, graph2.identifier))

        # TODO remove later
        assert not are_isomorphic(graph1, graph2)

    if iso1 == iso2:
        logger.debug(u"%s are isomorphic" % str_bit)
        return

    print u"Differences between %s." % str_bit

    in_both, in_first, in_second = compare.graph_diff(iso1, iso2)

    def dump_nt_sorted(g):
        return sorted(g.serialize(format='nt').splitlines())

    sorted_first = dump_nt_sorted(in_first)
    sorted_second = dump_nt_sorted(in_second)

    diff = difflib.unified_diff(
        sorted_first,
        sorted_second,
        u'Original',
        u'Current',
        lineterm=''
    )

    try:
        from pygments import highlight
        from pygments.formatters import terminal
        from pygments.lexers import web

        lexer = web.XmlLexer()
        formatter = terminal.TerminalFormatter()
        print highlight(u'\n'.join(diff), lexer, formatter)
    except ImportError:
        logger.info("Install pygments for colored diffs")
        print u'\n'.join(diff)
    except UnicodeDecodeError:
        print u"Only in first", unicode(sorted_first)
        print u"Only in second", unicode(sorted_second)