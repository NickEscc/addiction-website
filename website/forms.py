from django import forms
from allauth.account.forms import SignupForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class CustomSignupForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text='Required.')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
class CustomSignUpForm(SignupForm):
    first_name = forms.CharField(max_length=30, required=True, label='First Name')
    last_name = forms.CharField(max_length=30, required=True, label='Last Name')

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        user.save()
        return user
