from django.db import models

class Grade(models.Model):
    name = models.CharField(max_length=50)  
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} - {self.school.name}"

class Subject(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class TeacherAssignment(models.Model):
    teacher = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE)
    class Meta:
        unique_together = ('teacher', 'grade', 'subject', 'school')

    def __str__(self):
        return f"{self.teacher} → {self.subject} ({self.grade})"