# widgets.py (create this file in your blog app)
from django.forms.widgets import ClearableFileInput
from django.utils.datastructures import MultiValueDict
from django.core.files.uploadedfile import UploadedFile

class MultipleFileInput(ClearableFileInput):
    """
    Widget that allows multiple file uploads.
    """
    allow_multiple_selected = True
    
    def __init__(self, attrs=None):
        default_attrs = {'multiple': 'multiple'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def value_from_datadict(self, data, files, name):
        """
        Get the uploaded files.
        """
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        return [files.get(name)] if files.get(name) else []