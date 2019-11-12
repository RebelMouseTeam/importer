import collections
import glob

import lxml.etree

import preparation.flows
import preparation.wp.parsers as wp_parsers
import preparation.wp.extractors as wp_extractors
import preparation.flows.source
import preparation.flows.destination


class Preparator:
    extractors = []
    parser_cls = None
    source_flow_cls = None
    destination_flow_cls = None
    # supported_groups = ['posts', 'authors', 'sections', 'media', 'guest_authors']

    @classmethod
    def process(cls, source, destination):
        response = collections.defaultdict(dict)

        for content in cls.source_flow_cls.iterate_from_source(source):
            try:
                parsed_content = cls.parser_cls.parse(content)
            except lxml.etree.XMLSyntaxError:
                prepared_content = cls._prepare_content(content)
                try:
                    parsed_content = cls.parser_cls.parse(prepared_content)
                except:
                    with open('error.xml', 'wb') as f:
                        f.write(prepared_content)
                    raise
            for extractor in cls.extractors:
                for group, key, item in extractor.iterate(parsed_content):
                    response[group][key] = item

        # flattening response:
        response = {
            k: v.values()
            for k, v in response.items()
        }
        return cls.destination_flow_cls.move_to_destination(response, destination)

    @classmethod
    def _prepare_content(cls, content):
        broken_symbols = [
            b'\x00', b'\x01', b'\x02', b'\x03', b'\x04', b'\x05', b'\x06',
            b'\x08', b'\x0B', b'\x0C', b'\x10', b'\x11', b'\x13', b'\x14',
            b'\x17', b'\x18', b'\x19', b'\x1C', b'\x1D', b'\x1E',
        ]
        for i in broken_symbols:
            content = content.replace(i, b'')
        return content


class WpPreparator(Preparator):
    extractors = [wp_extractors.SectionExtractor, wp_extractors.ItemExtractor, wp_extractors.AuthorExtractor]
    parser_cls = wp_parsers.DefaultXmlParser
    source_flow_cls = preparation.flows.source.FileSourceFlow
    destination_flow_cls = preparation.flows.destination.MongoDestinationFlow
