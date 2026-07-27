from django.db import models


class School(models.Model):
    name = models.CharField(max_length=255)
    code = models.SlugField(max_length=50, unique=True)

    slogan = models.CharField(max_length=255, blank=True)
    about = models.TextField(blank=True)

    logo = models.ImageField(
        upload_to="schools/logos/",
        blank=True,
        null=True
    )

    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)

    address = models.CharField(max_length=255, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SchoolClass(models.Model):
    LEVEL_CHOICES = [
        ("pre_primary", "Pre-Primary"),
        ("lower_primary", "Lower Primary"),
        ("upper_primary", "Upper Primary"),
        ("junior_school", "Junior School"),
        ("senior_school", "Senior School"),
    ]

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="classes"
    )

    name = models.CharField(max_length=50)
    level = models.CharField(
        max_length=30,
        choices=LEVEL_CHOICES
    )

    order = models.PositiveSmallIntegerField(
        default=1,
        help_text="Used to sort classes."
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("school", "name")
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.school.name} - {self.name}"