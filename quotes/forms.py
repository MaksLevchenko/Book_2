from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

from .models import Quote, Source


class QuoteForm(forms.ModelForm):
    source_name = forms.CharField(max_length=255, label="Источник (название)")
    source_type = forms.ChoiceField(choices=Source.TYPE_CHOICES, label="Тип источника")

    class Meta:
        model = Quote
        fields = ["text", "weight", "source_name", "source_type"]
        labels = {
            "text": "Цитата",
            "weight": "Вес (>=1)",
        }

    def clean(self):
        cleaned = super().clean()
        weight = cleaned.get("weight")
        text = cleaned.get("text")
        source_name = cleaned.get("source_name")
        source_type = cleaned.get("source_type")
        if weight is not None and weight < 1:
            self.add_error("weight", "Вес должен быть >= 1")
        if text and Quote.objects.filter(text=text).exists():
            self.add_error("text", "Такая цитата уже существует")
        if source_name:
            source = Source.objects.filter(name=source_name).first()
            if source is None:
                return cleaned
            if source.quotes.count() >= 3:
                self.add_error("source_name", "У источника не может быть более 3 цитат")
        return cleaned

    def save(self, commit=True):
        source_name = self.cleaned_data["source_name"]
        source_type = self.cleaned_data["source_type"]
        source, _ = Source.objects.get_or_create(
            name=source_name, defaults={"type": source_type}
        )
        self.instance.source = source
        return super().save(commit)


class SignUpForm(UserCreationForm):
    class Meta:
        model = get_user_model()
        fields = ("username",)


class CommentForm(forms.Form):
    text = forms.CharField(
        label="Комментарий", widget=forms.Textarea(attrs={"rows": 3})
    )
    parent_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
