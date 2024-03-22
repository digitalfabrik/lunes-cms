from import_export.admin import ExportActionMixin
from import_export import fields, resources
from ..models import Document
from import_export.widgets import ForeignKeyWidget

class IsAudioWidget(ForeignKeyWidget): 
    model= Document
    field= "Audio"
    def __init__(self):
        super().__init__(Document, "audio")

    def render (self, value, obj= None): 
        return str(bool(value)) 


class DocumentResource(resources.ModelResource): 
    ExportActionMixin.export_admin_action

    word = fields.Field (
        column_name= "Word",
        attribute= "word"
    )

    word_type = fields.Field (
        column_name= "Word type",
        attribute= "word_type"
    )

    article = fields.Field (
        column_name= "Article",
        attribute= "article"
    )

    has_audio = fields.Field (
        column_name= "Has audio?",
        attribute= "word",
        widget= IsAudioWidget()
    )

    example_sentence = fields.Field (
        column_name= "Example sentence",
        attribute= "example_sentence"
    )

    creation_date = fields.Field (
        column_name= "Creation date",
        attribute= "creation_date"
    )

    #training_set_name = fields.Field (
    #    column_name= "Training Set",
    #    attribute= "training_set"
    #)
    #document_fields["training_set_name"] = " | ".join([t.title for t in document.training_sets .filter (discipline=profession) ])
    
    class Meta: 
        model= Document
        fields= ()

