from django.contrib import admin
from .models import (
    Assignment,
    Question,
    Submission,
    QuizAttempt,
    QuizAnswer,
    Enrollment,
    Subject,
)


# ----------------------------
# Inline Models
# ----------------------------
class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1


class QuizAnswerInline(admin.TabularInline):
    model = QuizAnswer
    extra = 0
    readonly_fields = ("is_correct",)


# ----------------------------
# Assignment
# ----------------------------
@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "teacher",
        "school_class",
        "subject",
        "assignment_type",
        "due_date",
        "created_at",
    )
    list_filter = (
        "assignment_type",
        "school_class",
        "subject",
        "created_at",
    )
    search_fields = (
        "title",
        "teacher__username",
        "teacher__first_name",
        "teacher__last_name",
    )
    date_hierarchy = "created_at"
    inlines = [QuestionInline]


# ----------------------------
# Question
# ----------------------------
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "assignment",
        "text",
        "correct_option",
        "marks",
    )
    list_filter = ("assignment",)
    search_fields = ("text",)


# ----------------------------
# Submission
# ----------------------------
@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "assignment",
        "student",
        "submitted_at",
        "marks",
        "graded",
    )
    list_filter = ("graded", "submitted_at")
    search_fields = (
        "student__username",
        "assignment__title",
    )


# ----------------------------
# Quiz Attempt
# ----------------------------
@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "assignment",
        "student",
        "score",
        "total",
        "is_graded",
        "started_at",
    )
    list_filter = ("is_graded",)
    search_fields = (
        "student__username",
        "assignment__title",
    )
    readonly_fields = (
        "score",
        "total",
        "started_at",
        "submitted_at",
    )
    inlines = [QuizAnswerInline]


# ----------------------------
# Quiz Answer
# ----------------------------
@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "attempt",
        "question",
        "selected_option",
        "is_correct",
    )
    list_filter = ("is_correct",)


# ----------------------------
# Enrollment
# ----------------------------
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "school_class",
        "school",
    )

    list_filter = (
        "school",
        "school_class",
    )

    search_fields = (
        "student__username",
        "student__first_name",
        "student__last_name",
    )

    autocomplete_fields = (
        "student",
        "school_class",
    )

    list_editable = (
        "school_class",
    )
# ----------------------------
# Subject
# ----------------------------
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "school",
    )
    list_filter = ("school",)
    search_fields = (
        "name",
        "code",
    )