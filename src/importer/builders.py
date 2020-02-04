import collections
import datetime
import re

# from scraper.embed_facade import get_embed


class BodyHandler:
    TW_URI_RE = re.compile(r'(?<!")https?://twitter.com/(?P<user>\w+)/status/(?P<embed_id>\d+)\/?(photo\/\d+)?(\?[\w_]+[=\w\d\%\^]+)?')
    YOUTUBE_RE = re.compile(r'(?<!\[youtube)(^|[^\"\'])(?P<youtube>http[s]?://(?:www\.)?(?:youtube\.com|youtu\.be).*?)(\s+|$|\<|\[)')
    CAPTION_RE = re.compile(r'\[caption[^\]]*?\](?P<text>.*?)\[\/caption\]', flags=re.IGNORECASE)

    @classmethod
    def caption(cls, text):
        return re.sub(cls.CAPTION_RE, cls.__caption_replace, text)

    @classmethod
    def twitter(cls, text):
        return re.sub(cls.TW_URI_RE, cls.__tw_replace, text)

    @classmethod
    def youtube(cls, text):
        return re.sub(cls.YOUTUBE_RE, cls.__youtube_replace, text)

    @staticmethod
    def __caption_replace(elem):
        if len(elem.groups()) == 1:
            try:
                return elem.groups()['text']
            except Exception:
                pass
        return elem

    @staticmethod
    def __tw_replace(elem):
        url = 'https://twitter.com/{}/status/{}'.format(
            elem.groupdict()['user'],
            elem.groupdict()['embed_id']
        )
        shortcode_text = '[twitter_embed {} expand=1]'.format(url)
        if not shortcode_text:
            return ''
        return shortcode_text

    @staticmethod
    def __youtube_replace(elem):
        try:
            url = elem.groupdict()['youtube']
            shortcode_text = '[youtube {} expand=1]'.format(url)
            if not shortcode_text:
                return elem.groupdict()['youtube']
            return elem.group(1) + shortcode_text + elem.group(3)
        except Exception:
            return ''


class FieldHandlers:
    @classmethod
    def as_is(cls, value):
        return value

    @classmethod
    def wp_pub_date(cls, value):
        dt = datetime.datetime.strptime(value, '%a, %d %b %Y %H:%M:%S %z')
        return int(dt.timestamp())

    @classmethod
    def basename(cls, value):
        filtered_value = re.sub(r'[^\w\d_-]', cls._sub_empty, value)
        return filtered_value[:200]

    @staticmethod
    def _sub_empty(value):
        return ''


class PostBuilder(object):
    primitive_mapping = {
        # 'post_field': (wp_field, parse_func),
        'headline': ('title', FieldHandlers.as_is),
        'body': ('content', FieldHandlers.as_is),
        'subheadline': ('excerpt', FieldHandlers.as_is),
        'manual_basename': ('name', FieldHandlers.basename),
    }

    # meta
    IMAGE_POSTMETA_KEYS = ['_thumbnail_id']
    EMBED_POSTMETA_KEYS = ['_nectar_video_embed', 'video_post_url', 'Tm_video_url', '_format_video_embed']

    # sections
    PUBLISH_TO_FRONTPAGE = True
    ALLOW_UNCATEGORIZED = False

    STATUS_MAP = {
        'publish': 'post',
        'private': 'draft',
        'draft': 'draft',
        'pending': 'draft',
        'trash': None,
    }

    def __init__(self, api, authors_manager, sections_manager, attachments_manager):
        self.authors = authors_manager
        self.attachments = attachments_manager
        self.sections = sections_manager
        self.api = api

    def _build_base_entry(self):
        entry = {
            'roar_specific_data': {},
            'sections': [],
            'tags': [],
        }
        return entry

    def build_entry(self, item):
        entry = self._build_base_entry()
        for rm_field, (wp_field, parse_func) in self.primitive_mapping.items():
            entry[rm_field] = parse_func(item[wp_field])
        entry['status'] = self.get_status(item)
        entry['tags'] = self.get_tags(item)
        entry['sections'] = self.get_sections(item)
        entry['roar_author_ids'] = self.get_roar_author_ids(item)
        entry['roar_specific_data']['original_item'] = item
        meta = self.build_meta(item['meta'])
        entry['roar_specific_data']['meta'] = meta
        entry.update(self.get_dates(item))
        entry.update(self.get_lead_image(meta))
        # entry.update(self.get_meta_embeds(meta))
        entry['body'] = self.prepare_body(entry['body'])
        return entry

    def prepare_body(self, body):
        # TODO: body processing
        body = BodyHandler.caption(body)
        body = BodyHandler.twitter(body)
        body = BodyHandler.youtube(body)
        return body

    def publish_entry(self, entry):
        # filter fields
        # check dates for future posts
        # publish post/draft
        # return post
        status = entry.pop('status')
        response = self.api.create_draft(**entry)
        if status == 'post':
            self.api.publish_draft(response['id'])
        return response

    def postpublish(self, post):
        # TODO: create redirects for current slug and for old slugs
        return post

    def build_meta(self, item_meta):
        meta = collections.defaultdict(list)
        for k, v in item_meta:
            meta[k].append(v)
        return meta

    def get_status(self, item):
        if item['password']:
            return 'draft'
        return self.STATUS_MAP[item['status']]

    def get_tags(self, item):
        categories = item['category']
        tags = []
        for cat in categories:
            if cat['domain'] == 'post_tag':
                tags.append(cat['text'])
        return tags

    def get_roar_author_ids(self, item):
        author_id = self.authors.get_by_key(item['creator'])
        return [author_id]

    def get_sections(self, item):
        categories = item['category']
        sections = []
        for cat in categories:
            if cat['domain'] == 'category':
                slug = cat['nicename']
                if slug == 'uncategorized' and not self.ALLOW_UNCATEGORIZED:
                    continue
                # sections.append(self.sections.get_by_slug(slug))
                sections.append(slug)
        if self.PUBLISH_TO_FRONTPAGE:
            sections.append('Home')
        return sections

    def get_dates(self, item):
        response = {}
        try:
            response['created_ts'] = FieldHandlers.wp_pub_date(item['pub_date'])
        except TypeError:
            pass
        # TODO: check for scheduling
        return response

    def get_lead_image(self, meta):
        for field_name in self.IMAGE_POSTMETA_KEYS:
            if field_name in meta:
                try:
                    thumb_id = int(meta[field_name][0])
                except ValueError:
                    continue
                image_info = self.attachments.get_image_info_by_id(thumb_id)
                if image_info and 'image_id' in image_info:
                    response = {
                        'image_id': image_info['image_id'],
                        'type': 'image',
                    }
                    caption, credit = self.attachments.get_caption_and_credit(thumb_id)
                    if caption:
                        response['photo_caption'] = caption
                    if credit:
                        response['photo_credit'] = credit
                    return response
        return {}
