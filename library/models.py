from django.conf import settings
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


# =========================
# LEVEL
# =========================
class Level(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name


class CurriculumClass(models.Model):
    level = models.ForeignKey(
        Level,
        on_delete=models.CASCADE,
        related_name="classes",
    )
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        unique_together = ("level", "name")

    def __str__(self):
        return f"{self.level} - {self.name}"


# =========================
# SUBJECT
# =========================
class Subject(models.Model):
    curriculum_class = models.ForeignKey(
        CurriculumClass,
        on_delete=models.CASCADE,
        related_name="subjects",
    )
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=20, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        unique_together = ("curriculum_class", "name")

    def __str__(self):
        return self.name


# =========================
# TOPIC
# =========================
class Topic(models.Model):
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="topics",
    )
    title = models.CharField(max_length=200)
    description = CKEditor5Field("Description", config_name="default")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        unique_together = ("subject", "title")

    def __str__(self):
        return self.title


# =========================
# SUBTOPIC
# =========================
class SubTopic(models.Model):
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="subtopics",
    )
    title = models.CharField(max_length=200)
    description = CKEditor5Field("Description", config_name="default")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


# =========================
# LESSON
# =========================
class Lesson(models.Model):
    subtopic = models.ForeignKey(
        SubTopic,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    introduction = CKEditor5Field(config_name="default", blank=True)
    learning_objectives = CKEditor5Field(config_name="default", blank=True)
    summary = CKEditor5Field(config_name="default", blank=True)
    estimated_minutes = models.PositiveIntegerField(default=20)
    thumbnail = models.ImageField(upload_to="lesson_thumbnails/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


# =========================
# RESOURCE TYPES
# =========================
class ResourceType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=20, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name


class AccessLevel(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Visibility(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


# =========================
# RESOURCE
# =========================
class Resource(models.Model):
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="resources",
    )
    resource_type = models.ForeignKey(
        ResourceType,
        on_delete=models.PROTECT,
        related_name="resources",
    )
    access_level = models.ForeignKey(
        AccessLevel,
        on_delete=models.PROTECT,
        related_name="resources",
    )
    visibility = models.ForeignKey(
        Visibility,
        on_delete=models.PROTECT,
        related_name="resources",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    description = CKEditor5Field(config_name="default", blank=True)
    file = models.FileField(upload_to="library/", blank=True, null=True)
    external_url = models.URLField(blank=True, null=True)
    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration in minutes for audio/video.",
    )
    thumbnail = models.ImageField(upload_to="resource_thumbnails/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)
    downloads = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# =========================
# ASSESSMENT
# =========================
class Assessment(models.Model):
    ASSESSMENT_TYPES = (
        ("quiz", "Quiz"),
        ("assignment", "Assignment"),
        ("cat", "CAT"),
        ("exam", "Exam"),
        ("practice", "Practice"),
    )

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    title = models.CharField(max_length=255)
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPES)
    instructions = CKEditor5Field(config_name="default", blank=True)
    time_limit = models.PositiveIntegerField(default=20, help_text="Minutes")
    passing_score = models.PositiveIntegerField(default=50)
    attempts_allowed = models.PositiveIntegerField(default=3)
    randomize_questions = models.BooleanField(default=True)
    show_answers = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# =========================
# QUESTION
# =========================
class Question(models.Model):
    QUESTION_TYPES = (
        ("mcq", "Multiple Choice"),
        ("true_false", "True/False"),
        ("short", "Short Answer"),
        ("essay", "Essay"),
    )

    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    question = CKEditor5Field(config_name="default")
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    answer = models.CharField(max_length=1)
    explanation = CKEditor5Field(config_name="default", blank=True)
    marks = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)


class AssessmentAttempt(models.Model):
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    passed = models.BooleanField(default=False)


class StudentAnswer(models.Model):
    attempt = models.ForeignKey(
        AssessmentAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.CharField(max_length=20)
    is_correct = models.BooleanField(default=False)
    marks_awarded = models.PositiveIntegerField(default=0)


# =========================
# PROGRESS
# =========================
class LessonProgress(models.Model):
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="progress",
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("not_started", "Not Started"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
        ],
        default="not_started",
    )
    percentage = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("learner", "lesson")


class ResourceView(models.Model):
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now=True)
    duration = models.PositiveIntegerField(default=0, help_text="Seconds viewed")
    completed = models.BooleanField(default=False)
    downloads = models.PositiveIntegerField(default=0)


class LessonNote(models.Model):
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    note = CKEditor5Field()
    updated_at = models.DateTimeField(auto_now=True)


class RecentlyViewed(models.Model):
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now=True)


# =========================
# PRODUCTS
# =========================
class Product(models.Model):
    title = models.CharField(max_length=255)
    description = CKEditor5Field(config_name="default")
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    thumbnail = models.ImageField(upload_to="products/")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ProductResource(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)


class Purchase(models.Model):
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    purchased_at = models.DateTimeField(auto_now_add=True)
    payment_reference = models.CharField(max_length=100)


class ProductCategory(models.Model):
    name = models.CharField(max_length=255)
    icon = models.CharField(max_length=100, blank=True)


class ProductReview(models.Model):
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField()
    review = models.TextField(blank=True)


# =========================
# SUBSCRIPTIONS
# =========================
class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    yearly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True)


class Subscription(models.Model):
    school = models.CharField(max_length=255, blank=True)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    active = models.BooleanField(default=True)


# =========================
# PAYMENTS
# =========================
class Wallet(models.Model):
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)


class Payout(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, default="pending")


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2)
    expires = models.DateField(null=True, blank=True)