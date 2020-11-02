from rest_framework import serializers

from .models import Field, TrainingSet, Document, AlternativeWord

class FieldSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Field
        fields = ('title', 'description')

class TrainingSetSerializer(serializers.HyperlinkedModelSerializer):
    field = FieldSerializer()
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