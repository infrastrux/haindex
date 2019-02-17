# -*- coding: UTF-8 -*-
from django_elasticsearch_dsl import DocType, Index, fields
from elasticsearch_dsl.query import MultiMatch

from haindex import models

search_index = Index('haindex')
search_index.settings(
    number_of_shards=1,
    number_of_replicas=0
)


@search_index.doc_type
class RepositoryDocument(DocType):
    keywords_text = fields.TextField()

    class Meta:
        model = models.Repository
        fields = [
            'readme',
            'description',
            'github_user',
            'github_repo',
        ]
        queryset_pagination = 100

    def get_queryset(self):
        """
        order queryset for consistent pagination
        """
        return super().get_queryset().order_by('id')

    def prepare_keywords_text(self, instance):
        if instance.keywords is not None:
            return ' '.join(instance.keywords)
        return ''

    @classmethod
    def search_all(cls, term):
        query = MultiMatch(query=term, fuzziness=2, fields=[
            'github_user^3', 'github_repo^3', 'description', 'readme'
        ])
        return cls.search().query(query)
