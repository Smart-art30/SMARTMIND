
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django_ckeditor_5.fields import CKEditor5Field


# =========================
# LEVEL
# =========================
class Level(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


# =========================
# SUBJECT
# =========================
class Subject(models.Model):
    level = models.ForeignKey(
        Level,
        on_delete=models.CASCADE,
        related_name='subjects'
    )
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        unique_together = ('level', 'name')
        indexes = [
            models.Index(fields=['level', 'name']),
        ]


# =========================
# TOPIC
# =========================
class Topic(models.Model):
    level = models.ForeignKey(
        Level,
        on_delete=models.CASCADE,
        related_name='topics',
        editable=False
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='topics'
    )

    title = models.CharField(max_length=200)
    description = CKEditor5Field("Description", config_name="default")

    def save(self, *args, **kwargs):
        if self.subject:
            self.level = self.subject.level
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['title']
        unique_together = ('subject', 'title')
        indexes = [
            models.Index(fields=['subject', 'title']),
        ]


# =========================
# SUBTOPIC
# =========================
class SubTopic(models.Model):
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='subtopics'
    )

    title = models.CharField(max_length=200)
    description = CKEditor5Field("Description", config_name="default")

    def __str__(self):
        return f"{self.topic.title} - {self.title}"

    class Meta:
        ordering = ['title']
        unique_together = ('topic', 'title')
        indexes = [
            models.Index(fields=['topic', 'title']),
        ]


# =========================
# RESOURCE
# =========================
class Resource(models.Model):
    RESOURCE_TYPES = (
        ('note', 'Notes'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('assignment', 'Assignment'),
        ('pastpaper', 'Past Paper'),
    )

    level = models.ForeignKey(
        Level,
        on_delete=models.CASCADE,
        related_name='resources',
        null=True,
        blank=True
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='resources',
        null=True,
        blank=True
    )
    target_classes = models.ManyToManyField(
    "schools.SchoolClass",
    blank=True,
    related_name="resources"
    )

    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='resources',
        null=True,
        blank=True
    )

    subtopic = models.ForeignKey(
        SubTopic,
        on_delete=models.CASCADE,
        related_name='resources',
        null=True,
        blank=True
    )
    embedding = models.JSONField(
    null=True,
    blank=True
)

    title = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    file = models.FileField(
        upload_to='library_resources/',
        blank=True,
        null=True
    )
    video_url = models.URLField(blank=True, null=True)
    description = CKEditor5Field("Description", config_name="default")
    created_at = models.DateTimeField(auto_now_add=True)
    views = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.subtopic:
            self.topic = self.subtopic.topic
            self.subject = self.topic.subject
            self.level = self.topic.level

        elif self.topic:
            self.subject = self.topic.subject
            self.level = self.topic.level

        super().save(*args, **kwargs)

    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']


# =========================
# QUESTION
# =========================
class Question(models.Model):
    level = models.ForeignKey(
        Level,
        on_delete=models.CASCADE,
        related_name='questions',
        null=True,
        blank=True
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='questions',
        null=True,
        blank=True
    )

    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='questions',
        null=True,
        blank=True
    )

    subtopic = models.ForeignKey(
        SubTopic,
        on_delete=models.CASCADE,
        related_name='questions',
        null=True,
        blank=True
    )

    question = CKEditor5Field("Question", config_name="default")

    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)

    answer = models.CharField(
        max_length=1,
        validators=[
            RegexValidator(
                regex=r'^[ABCD]$',
                message='Answer must be A, B, C or D'
            )
        ]
    )

    def save(self, *args, **kwargs):
        if self.subtopic:
            self.topic = self.subtopic.topic
            self.subject = self.topic.subject
            self.level = self.topic.level

        elif self.topic:
            self.subject = self.topic.subject
            self.level = self.topic.level

        elif self.subject:
            self.level = self.subject.level

        super().save(*args, **kwargs)

    def __str__(self):
        return self.question[:60]

    def get_correct_option(self):
        return {
            'A': self.option_a,
            'B': self.option_b,
            'C': self.option_c,
            'D': self.option_d,
        }.get(self.answer, '')

    def get_all_options(self):
        return {
            'A': self.option_a,
            'B': self.option_b,
            'C': self.option_c,
            'D': self.option_d,
        }

    class Meta:
        ordering = ['-id']


# =========================
# PROGRESS
# =========================
class Progress(models.Model):
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_progress'
    )

    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='progress_records',
        null=True,
        blank=True
    )

    subtopic = models.ForeignKey(
        SubTopic,
        on_delete=models.CASCADE,
        related_name='progress_records',
        null=True,
        blank=True
    )

    score = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    date_completed = models.DateTimeField(
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):
        if self.subtopic:
            self.topic = self.subtopic.topic

        if self.completed and not self.date_completed:
            from django.utils import timezone
            self.date_completed = timezone.now()

        super().save(*args, **kwargs)

    def update_progress(self, score, completed=False):
        self.score = score
        self.completed = completed

        if completed:
            from django.utils import timezone
            self.date_completed = timezone.now()

        self.save()

    def __str__(self):
        if self.subtopic:
            return f"{self.learner} - {self.subtopic}"
        return f"{self.learner} - {self.topic}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['learner', 'subtopic'],
                name='unique_learner_subtopic'
            )
        ]
        ordering = ['-date_completed']

class ResourceView(models.Model):
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    resource = models.ForeignKey(
        'Resource',
        on_delete=models.CASCADE,
        related_name='view_history'
    )

    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-viewed_at']
        unique_together = ('learner', 'resource')

    def __str__(self):
        return f"{self.learner} viewed {self.resource}"
