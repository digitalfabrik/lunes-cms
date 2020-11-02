from rest_framework import serializers

from .models import Discipline, TrainingSet, Document, AlternativeWord

class DisciplineSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Discipline
        fields = ('title', 'description')

class TrainingSetSerializer(serializers.HyperlinkedModelSerializer):
    field = DisciplineSerializer()
    class Meta:
        model = TrainingSet
        fields = ('title', 'details', 'field')

class DocumentSerializer(serializers.HyperlinkedModelSerializer):
    training_set = TrainingSetSerializer()
    class Meta:
        model = Document
        fields = ('word', 'article', 'image', 'cropping', 'audio', 
        'creation_date', 'training_set')

class AlternativeWordSerializer(serializers.HyperlinkedModelSerializer):
    document = DocumentSerializer()
    class Meta:
        model = AlternativeWord
        fields = ('alt_word', 'document')
