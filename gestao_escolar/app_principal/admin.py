from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Informações pessoais", {"fields": ("first_name", "last_name", "email", "cpf", "telefone")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions", "role")}),
        ("Datas Importantes", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "cpf", "telefone", "role", "password1", "password2", "is_staff", "is_active")}
        ),
    )
    search_fields = ("username", "email", "cpf")
    ordering = ("username",)
