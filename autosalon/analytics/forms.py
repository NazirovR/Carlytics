from .models import Client, Visit
from django.contrib.auth.models import User
from django import forms
from datetime import timedelta

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ['username', 'password']

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        exclude = ['user']


class VisitCreateForm(forms.ModelForm):
    duration = forms.IntegerField(label="Длительность (в часах)", min_value=1)

    class Meta:
        model = Visit
        fields = ['time_in', 'purpose', 'duration']
        widgets = {
            'time_in': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.time_in:
            self.fields['time_in'].initial = self.instance.time_in.strftime('%Y-%m-%dT%H:%M')

    def save(self, commit=True):
        visit = super().save(commit=False)
        duration = self.cleaned_data['duration']
        visit.time_out = visit.time_in + timedelta(hours=duration)
        if commit:
            visit.save()
        return visit

class ClientEditForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'age', 'gender', 'phone_number']
        widgets = {
            'gender': forms.Select(choices=Client.gender, attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }