from django import forms
from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ('name', 'description', 'github_url', 'status')

    def clean_github_url(self):
        github_url = self.cleaned_data['github_url']
        if github_url and 'github.com' not in github_url:
            raise forms.ValidationError('Ссылка должна вести на GitHub.')
        return github_url
