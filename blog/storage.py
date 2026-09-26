# blog/storage.py
from cloudinary_storage.storage import RawMediaCloudinaryStorage


class PostDocumentStorage(RawMediaCloudinaryStorage):
    """
    Cloudinary storage for raw documents attached to posts:
    PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT, CSV, ZIP, RAR.
    """
    folder = "posts/attachments"