# -*- coding: UTF-8 -*-
from django_elasticsearch_dsl import DocType, Index, fields
from elasticsearch_dsl import analyzer
from elasticsearch_dsl.query import MultiMatch

from haindex import models

search_index = Index('haindex')
search_index.settings(
    number_of_shards=1,
    number_of_replicas=0
)

html_strip = analyzer(
    'html_strip',
    tokenizer="standard",
    filter=["standard", "lowercase", "stop", "snowball"],
    char_filter=["html_strip"]
)


@search_index.doc_type
class RepositoryDocument(DocType):
    keywords_text = fields.TextField()
    username = fields.TextField()
    readme = fields.StringField(
        analyzer=html_strip,
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )

    class Meta:
        model = models.Repository
        fields = [
            'name',
            'author_name',
            'description',
            'last_push',
            'type',
        ]
        queryset_pagination = 100

    def get_queryset(self):
        """
        order queryset for consistent pagination
        only index extensions with a package file
        """
        return super().get_queryset().order_by('id')

    def prepare_keywords_text(self, instance):
        if instance.keywords is not None:
            return ' '.join(instance.keywords)
        return ''

    def prepare_username(self, instance):
        return instance.user.username

    @classmethod
    def search_all(cls, term):
        query = MultiMatch(query=term, fuzziness=2, fields=[
            'username^5',
            'name^5',
            'keywords_text^3',
            'name',
            'author_name',
            'description',
            'readme',
        ])
        return cls.search().query(query)
