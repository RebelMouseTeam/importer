from importer import builders, managers


class ItemImporter:
    source_collection = None
    destination_collection = None
    original_key_fields = []

    def __init__(self, db, api):
        self.db = db
        self.api = api

    def upload_all(self):
        failed = []
        for original_item in self._iter_source_items():
            if self._is_processed(original_item):
                print('item already processed:', original_item['_id'])
                continue
            try:
                self.upload(original_item)
            except Exception as e:
                failed.append((original_item, e))
        return failed

    def upload(self, original_item):
        raise NotImplementedError

    def _iter_source_items(self):
        collection = self.db[self.source_collection]
        for item in collection.find({}):
            yield item

    def _is_processed(self, original_item):
        collection = self.db[self.destination_collection]
        query = {i: original_item[i] for i in self.original_key_fields}
        return bool(list(collection.find(query)))

    def _store_response(self, original_item, response):
        # store response and item's key in destination collection for future
        collection = self.db[self.destination_collection]
        item = {i: original_item[i] for i in self.original_key_fields}
        item['response'] = response
        return collection.insert_one(item)


class ImageImporter(ItemImporter):
    source_collection = 'attachments'
    destination_collection = 'imported_images'
    original_key_fields = ['id', 'url']

    def upload(self, original_item):
        response = self.api.upload_image(
            image_url=original_item['url'],
            caption=original_item['content'],
            credit=original_item['excerpt'],
            # alt='',
        )
        self._store_response(original_item, response)


class SectionsImporter(ItemImporter):
    source_collection = 'sections'
    destination_collection = 'imported_sections'
    original_key_fields = ['title', 'url']

    def upload(self, original_item):
        response = self.api.create_section(
            title=original_item['title'],
            url=original_item['url'],
        )
        self._store_response(original_item, response)


class AuthorsImporter(ItemImporter):
    source_collection = 'authors'
    destination_collection = 'imported_authors'
    original_key_fields = ['id', 'login']

    def upload(self, original_item):
        specific_data = {i: original_item[i] for i in self.original_key_fields}
        response = self.api.create_author(
            email=original_item['email'],
            name=original_item['login'],
            first_name=original_item['first_name'],
            last_name=original_item['last_name'],
            specific_data={
                'provider_user_key': original_item['login'],
                'provider_user_id': original_item['id'],
            },
        )
        self._store_response(original_item, response)


class PostsImporter(ItemImporter):
    source_collection = 'posts'
    destination_collection = 'imported_posts'
    original_key_fields = ['id']

    types_to_import = [u'post', u'page']

    def __init__(self, db, api):
        self.db = db
        self.api = api
        self.default_builder = builders.PostBuilder(
            api,
            managers.WpAuthorsManager(db),
            managers.WpSectionsManager(db),
            managers.StoredAttachmentsManager(db),
        )

    def upload(self, original_item):
        builder = self._pick_builder_for_item(original_item)
        if not builder:
            return
        entry = builder.build_entry(original_item)
        post = builder.publish_entry(entry)
        post = builder.postpublish(post)
        self._store_response(original_item, post)
        print('post:', post['id'])

    def _pick_builder_for_item(self, item):
        if item['type'] not in self.types_to_import:
            print('skipping item with type:', item['type'])
            return
        return self.default_builder
