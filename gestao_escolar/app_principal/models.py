from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        PROFESSOR = "PROFESSOR", "Professor"
        ALUNO = "ALUNO", "Aluno"

    cpf = models.CharField(max_length=11, unique=True, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.ALUNO)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
