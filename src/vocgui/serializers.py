from rest_framework import serializers

from .models import Discipline, TrainingSet, Document, AlternativeWord, DocumentImage


class DisciplineSerializer(serializers.ModelSerializer):
    """
    Serializer for the Discipline module. Inherits from
    `serializers.ModelSerializer`.
    """

    total_training_sets = serializers.IntegerField()

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
        )


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
        fields = ("alt_word", "article", "plural_article")

    def to_representation(self, data):
        data = super(AlternativeWordSerializer, self).to_representation(data)
        if data['article'] == "die (Plural)":
            data['article'] = "die"
            data['plural_article'] = True
        else:
            data['plural_article'] = False
        return data


class DocumentImageSerializer(serializers.ModelSerializer):
    """
    Serializer for the DocumentImage module. Inherits from
    `serializers.ModelSerializer`.
    """

    class Meta:
        """
        Define model and the corresponding fields
        """

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
            "plural_article",
            "audio",
            "word_type",
            "alternatives",
            "document_image",
        )

    # modifys data to deliver the correct articles to frontend
    def to_representation(self, data):
        data = super(DocumentSerializer, self).to_representation(data)
        if data['article'] == "die (Plural)":
            data['article'] = "die"
            data['plural_article'] = True
        else:
            data['plural_article'] = False
        return data

