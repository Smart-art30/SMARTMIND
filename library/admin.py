from django.contrib import admin
from .models import (
    Level,
    CurriculumClass,
    Subject,
    Topic,
    SubTopic,
    Lesson,
    Resource,
    ResourceType,
    AccessLevel,
    Visibility,
    Assessment,
    Question,
    AssessmentAttempt,
    StudentAnswer,
    LessonProgress,
    Product,
    ProductResource,
    Purchase,
)


# =====================================================
# LEVEL
# =====================================================
@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "order")
    search_fields = ("name",)
    ordering = ("order",)


# =====================================================
# CURRICULUM CLASS
# =====================================================
@admin.register(CurriculumClass)
class CurriculumClassAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "level", "order")
    list_filter = ("level",)
    search_fields = ("name", "level__name")
    autocomplete_fields = ("level",)
    ordering = ("level", "order")


# =====================================================
# SUBJECT
# =====================================================
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "curriculum_class",
        "order",
    )

    list_filter = (
        "curriculum_class",
    )

    search_fields = (
        "name",
        "curriculum_class__name",
        "curriculum_class__level__name",
    )

    autocomplete_fields = (
        "curriculum_class",
    )

    ordering = (
        "curriculum_class",
        "order",
    )


# =====================================================
# TOPIC
# =====================================================
@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "subject",
        "curriculum_class",
    )

    list_filter = (
        "subject",
        "subject__curriculum_class",
    )

    search_fields = (
        "title",
        "subject__name",
    )

    autocomplete_fields = (
        "subject",
    )

    def curriculum_class(self, obj):
        return obj.subject.curriculum_class


# =====================================================
# SUBTOPIC
# =====================================================
@admin.register(SubTopic)
class SubTopicAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "topic",
        "subject",
    )

    list_filter = (
        "topic",
        "topic__subject",
    )

    search_fields = (
        "title",
        "topic__title",
    )

    autocomplete_fields = (
        "topic",
    )

    def subject(self, obj):
        return obj.topic.subject


# =====================================================
# LESSON
# =====================================================
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "subtopic",
        "estimated_minutes",
        "is_published",
        "created_at",
    )

    list_filter = (
        "is_published",
        "subtopic",
    )

    search_fields = (
        "title",
        "subtopic__title",
    )

    autocomplete_fields = (
        "subtopic",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


# =====================================================
# RESOURCE TYPE
# =====================================================
@admin.register(ResourceType)
class ResourceTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "icon",
        "color",
        "order",
    )
    search_fields = ("name",)


# =====================================================
# ACCESS LEVEL
# =====================================================
@admin.register(AccessLevel)
class AccessLevelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
    )
    search_fields = ("name",)


# =====================================================
# VISIBILITY
# =====================================================
@admin.register(Visibility)
class VisibilityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
    )
    search_fields = ("name",)


# =====================================================
# RESOURCE
# =====================================================
@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "lesson",
        "resource_type",
        "access_level",
        "visibility",
        "uploaded_by",
        "views",
        "downloads",
        "created_at",
    )

    list_filter = (
        "resource_type",
        "access_level",
        "visibility",
        "created_at",
    )

    search_fields = (
        "title",
        "lesson__title",
    )

    autocomplete_fields = (
        "lesson",
        "resource_type",
        "access_level",
        "visibility",
        "uploaded_by",
    )

    readonly_fields = (
        "views",
        "downloads",
        "created_at",
        "updated_at",
    )


# =====================================================
# ASSESSMENT
# =====================================================
@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "lesson",
        "assessment_type",
        "passing_score",
        "is_published",
    )

    list_filter = (
        "assessment_type",
        "is_published",
    )

    search_fields = (
        "title",
        "lesson__title",
    )

    autocomplete_fields = (
        "lesson",
    )


# =====================================================
# QUESTION
# =====================================================
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "assessment",
        "short_question",
        "answer",
        "marks",
    )

    list_filter = (
        "assessment",
    )

    search_fields = (
        "question",
        "assessment__title",
    )

    autocomplete_fields = (
        "assessment",
    )

    def short_question(self, obj):
        return str(obj.question)[:80]

    short_question.short_description = "Question"


# =====================================================
# ASSESSMENT ATTEMPT
# =====================================================
@admin.register(AssessmentAttempt)
class AssessmentAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "learner",
        "assessment",
        "score",
        "percentage",
        "passed",
        "completed_at",
    )

    search_fields = (
        "learner__username",
        "assessment__title",
    )

    list_filter = (
        "passed",
    )

    autocomplete_fields = (
        "learner",
        "assessment",
    )


# =====================================================
# STUDENT ANSWERS
# =====================================================
@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "attempt",
        "question",
        "selected_answer",
        "is_correct",
        "marks_awarded",
    )

    search_fields = (
        "question__question",
        "attempt__learner__username",
    )

    autocomplete_fields = (
        "attempt",
        "question",
    )


# =====================================================
# LESSON PROGRESS
# =====================================================
@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = (
        "learner",
        "lesson",
        "status",
        "percentage",
        "last_accessed",
    )

    list_filter = (
        "status",
    )

    autocomplete_fields = (
        "learner",
        "lesson",
    )

    readonly_fields = (
        "started_at",
        "completed_at",
        "last_accessed",
    )


# =====================================================
# PRODUCT
# =====================================================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "creator",
        "price",
        "is_active",
        "created_at",
    )

    search_fields = (
        "title",
        "creator__username",
    )

    list_filter = (
        "is_active",
    )

    autocomplete_fields = (
        "creator",
    )


# =====================================================
# PRODUCT RESOURCE
# =====================================================
@admin.register(ProductResource)
class ProductResourceAdmin(admin.ModelAdmin):
    autocomplete_fields = (
        "product",
        "resource",
    )


# =====================================================
# PURCHASE
# =====================================================
@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "learner",
        "product",
        "amount",
        "purchased_at",
    )

    autocomplete_fields = (
        "learner",
        "product",
    )