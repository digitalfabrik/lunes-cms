from django.contrib.auth.models import Group
from rest_framework import serializers

from .models import Discipline, TrainingSet, Document, AlternativeWord, DocumentImage
from .utils import get_child_count


class DisciplineSerializer(serializers.ModelSerializer):
    """
    Serializer for the Discipline module. Inherits from
    `serializers.ModelSerializer`.
    """

    total_training_sets = serializers.IntegerField()
    total_discipline_children = serializers.SerializerMethodField(
        "get_total_discipline_children"
    )

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = Discipline
        fields = (
            "id",
            "title",
            "description",
            "icon",
            "created_by",
            "total_training_sets",
            "total_discipline_children",
        )

    def get_total_discipline_children(self, obj):
        """Returns the total child count by calling
        utils.get_child_count(obj).


        :param disc: Discipline instance
        :type disc: models.Discipline
        :return: sum of children
        :rtype: int
        """
        return get_child_count(obj)


class TrainingSetSerializer(serializers.ModelSerializer):
    """
    Serializer for the TrainingSet module. Inherits from
    `serializers.ModelSerializer`.
    """

    total_documents = serializers.IntegerField()

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = TrainingSet
        fields = ("id", "title", "description", "icon", "total_documents")


class AlternativeWordSerializer(serializers.ModelSerializer):
    """
    Serializer for the AlternativeWord module. Inherits from
    `serializers.ModelSerializer`.
    """

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = AlternativeWord
        fields = ("alt_word", "article")


class DocumentImageListSerializer(serializers.ListSerializer):
    """
    List Serializer for the DocumentImage module. Inherits from
    `serializers.ListSerializer`.
    """

    def to_representation(self, data):
        """
        Overwrite django built-in function to only deliver
        approved images.

        :param data: model instance
        :type data: models.Model
        :return: serialized model data
        :rtype: dict
        """
        data = data.filter(confirmed=True)
        return super(DocumentImageListSerializer, self).to_representation(data)


class DocumentImageSerializer(serializers.ModelSerializer):
    """
    Serializer for the DocumentImage module. Inherits from
    `serializers.ModelSerializer`.
    """

    class Meta:
        """
        Define model and the corresponding fields
        """

        list_serializer_class = DocumentImageListSerializer
        model = DocumentImage
        fields = ("id", "image")


class DocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Document module. Inherits from
    `serializers.ModelSerializer`.
    """

    alternatives = AlternativeWordSerializer(many=True, read_only=True)
    document_image = DocumentImageSerializer(many=True, read_only=True)

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = Document
        fields = (
            "id",
            "word",
            "article",
            "audio",
            "word_type",
            "alternatives",
            "document_image",
        )


class GroupSerializer(serializers.ModelSerializer):
    """
    Serializer for the Group module. Inherits from
    `serializers.ModelSerializer`.
    """

    total_discipline_children = serializers.SerializerMethodField(
        "get_total_discipline_children"
    )

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = Group
        fields = (
            "id",
            "name",
            "icon",
            "total_discipline_children",
        )

    def get_total_discipline_children(self, obj):
        """Returns the total child count of a group.
        A child itself or one of its sub-children needs to
        contain at least one training set.

        :param disc: Discipline instance
        :type disc: models.Discipline
        :return: sum of children
        :rtype: int
        """
        queryset = Discipline.objects.filter(released=True, created_by=obj.id)
        queryset = [obj for obj in queryset if obj.is_root_node() and obj.is_valid()]
        return len(queryset)
