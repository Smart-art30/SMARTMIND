from django.db import models, transaction
from django.core.exceptions import ValidationError
from django_ckeditor_5.fields import CKEditor5Field
from schools.models import School, SchoolClass
from django.utils import timezone
from .storage import AssignmentStorage
from .storage import SubmissionStorage


class Assignment(models.Model):
    ASSIGNMENT_TYPES = (
        ('essay', 'Essay / Written'),
        ('quiz', 'Multiple Choice Quiz'),
        ('mixed', 'Mixed'),
    )

    title = models.CharField(max_length=200)
    description = CKEditor5Field("Description", config_name="default")
    teacher = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name="created_assignments"
    )
    from .storage import AssignmentStorage

    attachment = models.FileField(
        storage=AssignmentStorage(),
        upload_to="",
        blank=True,
        null=True,
    )
    school_class = models.ForeignKey(
        'schools.SchoolClass',
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    subject = models.ForeignKey(
        "Subject",
        on_delete=models.CASCADE,
        related_name="assignments"
    )
    assignment_type = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_TYPES,
        default='essay'
    )
    due_date = models.DateTimeField()
    total_marks = models.FloatField(default=100)
    duration_minutes = models.IntegerField(null=True, blank=True)
    is_timed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["school_class"]),
            models.Index(fields=["subject"]),
            models.Index(fields=["teacher"]),
            models.Index(fields=["due_date"]),
        ]

    def clean(self):
            super().clean()


            if self.due_date:
                
                if timezone.is_naive(self.due_date):
                    self.due_date = timezone.make_aware(
                        self.due_date,
                        timezone.get_current_timezone()
                    )

                if self.due_date <= timezone.now():
                    raise ValidationError({
                        "due_date": "Due date must be in the future."
                    })

            if self.is_timed:
                if not self.duration_minutes or self.duration_minutes <= 0:
                    raise ValidationError({
                        "duration_minutes": "Enter a valid duration."
                    })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Question(models.Model):
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="questions"
    )

    text = CKEditor5Field("Question", config_name="default")
    option_a = CKEditor5Field("Option A", config_name="default")
    option_b = CKEditor5Field("Option B", config_name="default")
    option_c = CKEditor5Field("Option C", config_name="default")
    option_d = CKEditor5Field("Option D", config_name="default")

    correct_option = models.CharField(
        max_length=1,
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]
    )
    marks = models.FloatField(default=1)
    explanation = CKEditor5Field(
        "Explanation",
        config_name="default",
        blank=True,
        null=True,
        help_text="Optional: explain why the correct answer is correct.",
    )

    class Meta:
        ordering = ['id']

    def clean(self):
        if not self.assignment_id:
            raise ValidationError({"assignment": "Assignment is required."})

        if self.assignment.assignment_type not in ['quiz', 'mixed']:
            raise ValidationError("Questions can only be added to quiz or mixed assignments.")

        if self.pk:
            question_count = self.assignment.questions.exclude(pk=self.pk).count()
        else:
            question_count = self.assignment.questions.count()

        if question_count >= 20:
            raise ValidationError("Quiz cannot exceed 20 questions.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.text)


class Submission(models.Model):
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    student = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    content = CKEditor5Field(
        'Submission',
        config_name='extends',
        blank=True,
        null=True
    )
    file = models.FileField(
    storage=SubmissionStorage(),
    upload_to="",
    blank=True,
    null=True,
)
    is_submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(
    blank=True,
    null=True
)
    marks = models.FloatField(null=True, blank=True)
    feedback = CKEditor5Field(
        'Feedback',
        config_name='extends',
        blank=True,
        null=True
    )
    graded = models.BooleanField(default=False)

    def clean(self):
        super().clean()

        # Only block NEW submissions after the deadline
        if self.assignment_id:
            due_date = self.assignment.due_date

            if timezone.is_naive(due_date):
                due_date = timezone.make_aware(
                    due_date,
                    timezone.get_current_timezone()
                )

            if due_date < timezone.now() and not self.pk:
                raise ValidationError(
                    "Submission deadline has passed."
                )

    
        if self.graded:
            return

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def percentage(self):
        if self.assignment.total_marks:
            return round((self.marks / self.assignment.total_marks) * 100, 2)
        return 0

    @property
    def is_open(self):
        due_date = self.assignment.due_date

        if timezone.is_naive(due_date):
            due_date = timezone.make_aware(
                due_date,
                timezone.get_current_timezone()
            )
            return timezone.now() <= due_date
    class Meta:
        unique_together = ('assignment', 'student')
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=["student"]),
            models.Index(fields=["assignment"]),
        ]

    def __str__(self):
        return f"{self.student} → {self.assignment}"

class QuizAttempt(models.Model):
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="attempts"
    )
    question_order = models.JSONField(default=list, blank=True)
    student = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name="quiz_attempts"
    )
    score = models.FloatField(default=0)
    total = models.FloatField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_graded = models.BooleanField(default=False)

    PASS_MARK = 50

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=["student"]),
            models.Index(fields=["assignment"]),
        ]

    @property
    def percentage(self):
        if not self.total:
            return 0
        return round((self.score / self.total) * 100, 1)

    @property
    def passed(self):
        return self.percentage >= self.PASS_MARK

    @property
    def attempt_number(self):
        """1-based index of this attempt among the student's attempts for this quiz."""
        return (
            QuizAttempt.objects
            .filter(
                assignment_id=self.assignment_id,
                student_id=self.student_id,
                id__lte=self.id,
            )
            .count()
        )

    def grade(self):
        if self.is_graded:
            return

        with transaction.atomic():
            score = 0
            total = 0

            for ans in self.answers.select_related("question"):
                total += ans.question.marks
                ans.is_correct = (
                    ans.selected_option == ans.question.correct_option
                )
                ans.save(update_fields=["is_correct"])

                if ans.is_correct:
                    score += ans.question.marks

            self.score = score
            self.total = total
            self.submitted_at = timezone.now()
            self.is_graded = True
            self.save(update_fields=[
                "score", "total", "submitted_at", "is_graded"
            ])

    @property
    def time_taken(self):
        if self.submitted_at:
            return self.submitted_at - self.started_at
        return timezone.now() - self.started_at

    def __str__(self):
        return f"{self.student} - {self.assignment}"

class QuizAnswer(models.Model):
    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name="answers"
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(
        max_length=1,
        blank=True,
        null=True
    )
    is_correct = models.BooleanField(default=False)

    class Meta:
        unique_together = ('attempt', 'question')

    @property
    def marks_awarded(self):
        return self.question.marks if self.is_correct else 0

    def __str__(self):
        return f"Attempt {self.attempt.id} - Question {self.question.id}"


class Enrollment(models.Model):
    student = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    school_class = models.ForeignKey(
        "schools.SchoolClass",
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        editable=False
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "school_class"],
                name="unique_student_class"
            )
        ]

    def save(self, *args, **kwargs):
        self.school = self.school_class.school
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.school_class}"


class Subject(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="subjects"
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ('school', 'name')

    def __str__(self):
        return f"{self.name} - {self.school.name}"