class SourceChecker:
    @classmethod
    def raise_for_source(cls, parsed_content):
        return True


class WpSourceChecker(SourceChecker):
    @classmethod
    def raise_for_source(cls, parsed_content):
        try:
            wp_ns = parsed_content.nsmap.get('wp')
        except (AttributeError, TypeError):
            raise ValueError('Content is not from WordPress')

        if '/wordpress.org/' not in wp_ns:
            raise ValueError('Content is not from WordPress')
        return True
