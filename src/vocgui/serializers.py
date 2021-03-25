from rest_framework import serializers

from .models import Discipline, TrainingSet, Document, AlternativeWord, DocumentImage


class DisciplineSerializer(serializers.ModelSerializer):
    total_training_sets = serializers.IntegerField()

    class Meta:
        model = Discipline
        fields = ('id', 'title', 'description', 'icon', 'total_training_sets')


class TrainingSetSerializer(serializers.ModelSerializer):
    total_documents = serializers.IntegerField()

    class Meta:
        model = TrainingSet
        fields = ('id', 'title', 'description', 'icon', 'total_documents')


class AlternativeWordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlternativeWord
        fields = ('alt_word', 'article')


class DocumentImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentImage
        fields = ('id', 'image')


class DocumentSerializer(serializers.ModelSerializer):
    alternatives = AlternativeWordSerializer(many=True, read_only=True)
    document_images = DocumentImageSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = ('id', 'word', 'article', 'audio', 'word_type', 'document_images', 'alternatives')
