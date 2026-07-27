from django import forms
from .models import (
    Resource,
    Subject,
    Topic,
    SubTopic,
    Level,
)
from schools.models import SchoolClass


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = [
            'level',
            'subject',
            'topic',
            'subtopic',
            'target_classes',   # <-- add this
            'title',
            'resource_type',
            'file',
            'video_url',
            'description',
        ]

        widgets = {
            'level': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'topic': forms.Select(attrs={'class': 'form-select'}),
            'subtopic': forms.Select(attrs={'class': 'form-select'}),
            'target_classes': forms.CheckboxSelectMultiple(),
          
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'resource_type': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['level'].queryset = Level.objects.all().order_by('name')
        self.fields['subject'].queryset = Subject.objects.all().order_by('name')
        self.fields['topic'].queryset = Topic.objects.none()
        self.fields['subtopic'].queryset = SubTopic.objects.none()

        # Only show classes belonging to the user's school
        if user and user.school:
            self.fields['target_classes'].queryset = SchoolClass.objects.filter(
                school=user.school,
                is_active=True
            ).order_by('order')
        else:
            self.fields['target_classes'].queryset = SchoolClass.objects.none()

        # Existing instance
        if self.instance.pk:
            if self.instance.subject:
                self.fields['topic'].queryset = Topic.objects.filter(
                    subject=self.instance.subject
                ).order_by('title')

            if self.instance.topic:
                self.fields['subtopic'].queryset = SubTopic.objects.filter(
                    topic=self.instance.topic
                ).order_by('title')

        # AJAX
        if 'subject' in self.data:
            try:
                subject_id = int(self.data.get('subject'))
                self.fields['topic'].queryset = Topic.objects.filter(
                    subject_id=subject_id
                ).order_by('title')
            except (TypeError, ValueError):
                pass

        if 'topic' in self.data:
            try:
                topic_id = int(self.data.get('topic'))
                self.fields['subtopic'].queryset = SubTopic.objects.filter(
                    topic_id=topic_id
                ).order_by('title')
            except (TypeError, ValueError):
                pass

    def clean(self):
        cleaned_data = super().clean()

        resource_type = cleaned_data.get('resource_type')
        file = cleaned_data.get('file')
        video_url = cleaned_data.get('video_url')

        if resource_type == 'video':
            if not video_url:
                self.add_error('video_url', 'Please provide a video URL.')
        else:
            if not file and not self.instance.pk:
                self.add_error('file', 'Please upload a file.')

        return cleaned_data