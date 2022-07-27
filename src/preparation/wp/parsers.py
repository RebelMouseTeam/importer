import lxml.etree

from preparation.errors import ContentSourceMismatchError


class DefaultXmlParser:
    @classmethod
    def parse(cls, content):
        doc = lxml.etree.fromstring(content, parser=lxml.etree.XMLParser(huge_tree=True))
        wp = doc.nsmap.get('wp')
        if not wp or '/wordpress.org/export/' not in wp.lower():
            raise ContentSourceMismatchError('WordPress export file expected.')
        return doc
