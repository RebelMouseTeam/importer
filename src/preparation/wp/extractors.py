from . import field_handlers


class ItemExtractorBase:
    @classmethod
    def iterate(cls, parsed_content):
        for item in cls._raw_iterator(parsed_content):
            prepared_item = cls._prepare_item(item)
            group = cls._get_item_group(prepared_item)
            key = cls._key_func(prepared_item)
            yield (group, key, prepared_item)

    @classmethod
    def _key_func(cls, prepared_item):
        return prepared_item['id']

    @classmethod
    def _get_item_group(cls, item):
        raise NotImplementedError

    @classmethod
    def _raw_iterator(cls, parsed_content):
        raise NotImplementedError

    @classmethod
    def _prepare_item(cls, item):
        return item


class ItemExtractor(ItemExtractorBase):
    @classmethod
    def _key_func(cls, prepared_item):
        return prepared_item['id']

    @classmethod
    def _get_item_group(cls, prepared_item):
        post_type = prepared_item['type']
        if post_type == 'attachment':
            return 'attachments'
        elif post_type == 'guest-author':
            return 'guest_authors'
        return 'posts'

    @classmethod
    def _raw_iterator(cls, parsed_content):
        for item in parsed_content.xpath('.//item', namespaces=parsed_content.nsmap):
            yield item

    @classmethod
    def _prepare_item(cls, item):
        item_type = item.xpath('.//wp:post_type', namespaces=item.nsmap)[0].text
        if item_type == 'attachment':
            return cls._prepare_attachment(item)

        prepared_item = {
            'title': item.xpath('.//title', namespaces=item.nsmap)[0].text,
            'link': item.xpath('.//link', namespaces=item.nsmap)[0].text,
            'pub_date': item.xpath('.//pubDate', namespaces=item.nsmap)[0].text,
            'creator': item.xpath('.//dc:creator', namespaces=item.nsmap)[0].text,
            'guid': item.xpath('.//guid', namespaces=item.nsmap)[0].text,
            'description': item.xpath('.//description', namespaces=item.nsmap)[0].text,
            'content': item.xpath('.//content:encoded', namespaces=item.nsmap)[0].text,
            'excerpt': item.xpath('.//excerpt:encoded', namespaces=item.nsmap)[0].text,
            'id': int(item.xpath('.//wp:post_id', namespaces=item.nsmap)[0].text),
            'date': item.xpath('.//wp:post_date', namespaces=item.nsmap)[0].text,
            'date_gmt': item.xpath('.//wp:post_date_gmt', namespaces=item.nsmap)[0].text,
            'name': item.xpath('.//wp:post_name', namespaces=item.nsmap)[0].text,
            'password': item.xpath('.//wp:post_password', namespaces=item.nsmap)[0].text,
            'parent': int(item.xpath('.//wp:post_parent', namespaces=item.nsmap)[0].text),
            'type': item_type,
            'status': item.xpath('.//wp:status', namespaces=item.nsmap)[0].text,
            'category': [],
        }

        for category in item.xpath('.//category', namespaces=item.nsmap):
            prepared_item['category'].append(field_handlers.attrib_dict_plus_text(category))

        prepared_item['meta'] = cls._extract_meta(item)
        return prepared_item

    @classmethod
    def _prepare_attachment(cls, item):
        meta = cls._extract_meta(item)
        prepared_item = {
            'title': item.xpath('.//title', namespaces=item.nsmap)[0].text,
            # 'link': item.xpath('.//link', namespaces=item.nsmap)[0].text,
            # 'creator': item.xpath('.//dc:creator', namespaces=item.nsmap)[0].text,
            'guid': item.xpath('.//guid', namespaces=item.nsmap)[0].text,
            'description': item.xpath('.//description', namespaces=item.nsmap)[0].text,
            'content': item.xpath('.//content:encoded', namespaces=item.nsmap)[0].text,
            'excerpt': item.xpath('.//excerpt:encoded', namespaces=item.nsmap)[0].text,
            'id': int(item.xpath('.//wp:post_id', namespaces=item.nsmap)[0].text),
            # 'date': item.xpath('.//wp:post_date', namespaces=item.nsmap)[0].text,
            # 'date_gmt': item.xpath('.//wp:post_date_gmt', namespaces=item.nsmap)[0].text,
            'name': item.xpath('.//wp:post_name', namespaces=item.nsmap)[0].text,
            'parent': int(item.xpath('.//wp:post_parent', namespaces=item.nsmap)[0].text),
            'type': item.xpath('.//wp:post_type', namespaces=item.nsmap)[0].text,
            # 'status': item.xpath('.//wp:status', namespaces=item.nsmap)[0].text,
            'url': item.xpath('.//wp:attachment_url', namespaces=item.nsmap)[0].text,
            'meta': meta,
            'alt': self._get_alt(meta),
        }
        return prepared_item

    @classmethod
    def _extract_meta(cls, item):
        meta = []
        for postmeta in item.xpath('.//wp:postmeta', namespaces=item.nsmap):
            key, value = field_handlers.postmeta_pair(postmeta)
            meta.append((key, value))
        return meta

    @classmethod
    def _get_alt(cls, meta):
        if not meta:
            return ''
        for key, value in meta:
            if key == '_wp_attachment_image_alt':
                return value
        return ''


class AuthorExtractor(ItemExtractorBase):
    handlers = {
        'wp:author_id': field_handlers.text_to_int,
    }

    @classmethod
    def iterate(cls, parsed_content):
        for item in cls._raw_iterator(parsed_content):
            prepared_item = cls._prepare_item(item)
            group = cls._get_item_group(prepared_item)
            key = cls._key_func(prepared_item)
            yield (group, key, prepared_item)

    @classmethod
    def _key_func(cls, prepared_item):
        return prepared_item.get('id', prepared_item['display_name'])

    @classmethod
    def _get_item_group(cls, item):
        return 'authors'

    @classmethod
    def _raw_iterator(cls, parsed_content):
        wp_authors = parsed_content.xpath('.//wp:author', namespaces=parsed_content.nsmap)
        authors = wp_authors or parsed_content.xpath('.//dc:creator', namespaces=parsed_content.nsmap)
        for author in authors:
            yield author

    @classmethod
    def _prepare_item(cls, item):
        if 'creator' in item.tag:
            return {'display_name': item.text}
        prepared_item = {
            'login': item.xpath('.//wp:author_login', namespaces=item.nsmap)[0].text,
            'email': item.xpath('.//wp:author_email', namespaces=item.nsmap)[0].text,
            'first_name': item.xpath('.//wp:author_first_name', namespaces=item.nsmap)[0].text,
            'display_name': item.xpath('.//wp:author_display_name', namespaces=item.nsmap)[0].text,
            'id': int(item.xpath('.//wp:author_id', namespaces=item.nsmap)[0].text),
            'last_name': item.xpath('.//wp:author_last_name', namespaces=item.nsmap)[0].text,
        }
        return prepared_item


class SectionExtractor(ItemExtractorBase):
    @classmethod
    def _key_func(cls, prepared_item):
        return prepared_item['url']

    @classmethod
    def _get_item_group(cls, item):
        return 'sections'

    @classmethod
    def _raw_iterator(cls, parsed_content):
        categories = parsed_content.findall('.//category[@domain="category"]')
        for category in categories:
            yield category

    @classmethod
    def _prepare_item(cls, item):
        return {'url': item.attrib['nicename'], 'title': item.text}
