
from django.contrib import admin
from .models import (
    Level,
    Subject,
    Topic,
    SubTopic,
    Resource,
    Question,
    Progress,
)


# =========================
# LEVEL ADMIN
# =========================
@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)


# =========================
# SUBJECT ADMIN
# =========================
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'level')
    list_filter = ('level',)
    search_fields = ('name', 'level__name')
    autocomplete_fields = ('level',)
    ordering = ('level', 'name')
    list_select_related = ('level',)


# =========================
# TOPIC ADMIN
# =========================
@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'subject',
        'get_level',
    )

    list_filter = (
        'subject__level',
        'subject',
    )

    search_fields = (
        'title',
        'subject__name',
        'subject__level__name',
    )

    autocomplete_fields = (
        'subject',
        'level',
    )

    ordering = (
        'subject__level',
        'subject',
        'title',
    )

    list_select_related = (
        'level',
        'subject',
    )

    def get_level(self, obj):
        return obj.level
    get_level.short_description = 'Level'


# =========================
# SUBTOPIC ADMIN
# =========================
@admin.register(SubTopic)
class SubTopicAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'topic',
        'get_subject',
        'get_level',
    )

    list_filter = (
        'topic__subject__level',
        'topic__subject',
        'topic',
    )

    search_fields = (
        'title',
        'topic__title',
        'topic__subject__name',
        'topic__subject__level__name',
    )

    autocomplete_fields = (
        'topic',
    )

    ordering = (
        'topic',
        'title',
    )

    list_select_related = (
        'topic',
        'topic__subject',
        'topic__level',
    )

    def get_subject(self, obj):
        return obj.topic.subject
    get_subject.short_description = 'Subject'

    def get_level(self, obj):
        return obj.topic.level
    get_level.short_description = 'Level'


# =========================
# RESOURCE ADMIN
# =========================
@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'resource_type',
        'level',
        'subject',
        'topic',
        'subtopic',
        'views',
        'created_at',
    )

    list_filter = (
        'resource_type',
        'level',
        'subject',
        'topic',
        'subtopic',
        'created_at',
    )

    search_fields = (
        'title',
        'description',
        'level__name',
        'subject__name',
        'topic__title',
        'subtopic__title',
    )

    autocomplete_fields = (
        'level',
        'subject',
        'topic',
        'subtopic',
    )

    readonly_fields = (
        'views',
        'created_at',
    )

    date_hierarchy = 'created_at'

    ordering = (
        '-created_at',
    )

    list_select_related = (
        'level',
        'subject',
        'topic',
        'subtopic',
    )


# =========================
# QUESTION ADMIN
# =========================
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'short_question',
        'level',
        'subject',
        'topic',
        'subtopic',
        'answer',
    )

    list_filter = (
        'level',
        'subject',
        'topic',
        'subtopic',
        'answer',
    )

    search_fields = (
        'question',
        'level__name',
        'subject__name',
        'topic__title',
        'subtopic__title',
    )

    autocomplete_fields = (
        'level',
        'subject',
        'topic',
        'subtopic',
    )

    ordering = (
        '-id',
    )

    list_select_related = (
        'level',
        'subject',
        'topic',
        'subtopic',
    )

    def short_question(self, obj):
        return obj.question[:80]
    short_question.short_description = 'Question'


# =========================
# PROGRESS ADMIN
# =========================
@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = (
        'learner',
        'topic',
        'subtopic',
        'score',
        'completed',
        'date_completed',
    )

    list_filter = (
        'completed',
        'topic',
        'subtopic',
        'date_completed',
    )

    search_fields = (
        'learner__username',
        'learner__first_name',
        'learner__last_name',
        'topic__title',
        'subtopic__title',
    )

    autocomplete_fields = (
        'learner',
        'topic',
        'subtopic',
    )

    readonly_fields = (
        'date_completed',
    )

    ordering = (
        '-date_completed',
    )

    list_select_related = (
        'learner',
        'topic',
        'subtopic',
    )

