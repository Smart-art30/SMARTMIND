from cloudinary_storage.storage import RawMediaCloudinaryStorage


class PostDocumentStorage(RawMediaCloudinaryStorage):
    """
    Cloudinary storage for raw documents attached to posts:
    PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT, CSV, ZIP, RAR.

    
    """

    def get_object_parameters(self, name):
        params = super().get_object_parameters(name) or {}
        params["folder"] = "posts/attachments"
        params["resource_type"] = "raw"
        params.pop("tags", None)  
        return params