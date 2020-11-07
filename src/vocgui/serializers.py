from rest_framework import serializers

from .models import Discipline, TrainingSet, Document, AlternativeWord

class DisciplineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discipline
        fields = ('id', 'title', 'description')

class TrainingSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingSet
        fields = ('id', 'title', 'description')

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('id', 'word', 'article', 'image', 'cropping', 'audio', 'alternatives')

class AlternativeWordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlternativeWord
        fields = ('alt_word', 'article')
