from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    cpf = forms.CharField(required=True, label="CPF", max_length=11)
    telefone = forms.CharField(required=False, label="Telefone", max_length=20)
    role = forms.ChoiceField(choices=CustomUser.Roles.choices, label="Tipo de Usuário")

    class Meta:
        model = CustomUser
        fields = ("username", "email", "cpf", "telefone", "role", "password1", "password2")
