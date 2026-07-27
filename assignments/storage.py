from cloudinary_storage.storage import RawMediaCloudinaryStorage


class AssignmentStorage(RawMediaCloudinaryStorage):
    folder = "assignments"


class SubmissionStorage(RawMediaCloudinaryStorage):
    folder = "submissions"