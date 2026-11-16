from django import forms
from django.contrib.auth import get_user_model
from .models import Category, Comment, ServiceRequest


class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ["category", "title", "description", "location", "priority"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if len(title) < 8:
            raise forms.ValidationError("Use at least 8 characters.")
        return title


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["body"].widget.attrs.setdefault("class", "form-control")

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if len(body) < 3:
            raise forms.ValidationError("Enter a meaningful comment.")
        return body


class AssignmentForm(forms.Form):
    technician = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        required=True,
        empty_label="Select technician",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["technician"].queryset = (
            get_user_model().objects.filter(is_active=True, is_staff=True).order_by("username")
        )
        self.fields["technician"].widget.attrs.setdefault("class", "form-control")


class ResolutionForm(forms.Form):
    work_notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "class": "form-control", "placeholder": "Technician work notes..."}),
        required=True,
        help_text="Detailed notes on maintenance performed.",
    )
    resolution_summary = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control", "placeholder": "Summary of resolution for requester..."}),
        required=True,
        help_text="Customer-facing summary explaining how the issue was resolved.",
    )

    def clean_work_notes(self):
        notes = self.cleaned_data["work_notes"].strip()
        if not notes:
            raise forms.ValidationError("Work notes are required.")
        return notes

    def clean_resolution_summary(self):
        summary = self.cleaned_data["resolution_summary"].strip()
        if not summary:
            raise forms.ValidationError("Resolution summary is required.")
        return summary
