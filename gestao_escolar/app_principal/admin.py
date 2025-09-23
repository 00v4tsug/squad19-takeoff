from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, UnidadeFederativa, Municipio, Perfil,
    LogAcesso, Status, TipoSetor, Setor, Solicitacao, SolicitacaoCadastro,
    Item, Combo, ItemCombo, Competencia, Aluno,
    SetorCombo, SetorComboItemCombo
)


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("username", "email", "cpf", "telefone", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email", "cpf")
    ordering = ("username",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Informações pessoais", {"fields": ("first_name", "last_name", "email", "cpf", "telefone", "data_nascimento", "filiacao_1", "filiacao_2", "endereco")}),
        ("Relacionamentos", {"fields": ("perfil", "municipio")}),
        ("Permissões", {"fields": ("role", "is_staff", "is_active", "is_superuser", "groups", "user_permissions")}),
        ("Datas importantes", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "cpf", "telefone", "role", "password1", "password2", "is_staff", "is_active"),
        }),
    )


@admin.register(UnidadeFederativa)
class UnidadeFederativaAdmin(admin.ModelAdmin):
    list_display = ("sigla", "nome_unidade_federativa")
    search_fields = ("sigla", "nome_unidade_federativa")


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ("nome_municipio", "unidade_federativa")
    search_fields = ("nome_municipio",)
    list_filter = ("unidade_federativa",)


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("nome_perfil", "descricao")
    search_fields = ("nome_perfil",)


@admin.register(LogAcesso)
class LogAcessoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "data_hora")
    list_filter = ("data_hora",)


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ("tipo_status", "descricao_status")
    search_fields = ("tipo_status",)


@admin.register(TipoSetor)
class TipoSetorAdmin(admin.ModelAdmin):
    list_display = ("tipo_descricao",)
    search_fields = ("tipo_descricao",)


@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo_setor", "setor_pai", "municipio", "usuario")
    search_fields = ("nome",)
    list_filter = ("tipo_setor", "municipio")


@admin.register(Solicitacao)
class SolicitacaoAdmin(admin.ModelAdmin):
    list_display = ("descricao_solicitacao", "setor", "status", "admin_responsavel", "data_solicitacao", "data_resposta")
    list_filter = ("status", "setor")
    search_fields = ("descricao_solicitacao",)


@admin.register(SolicitacaoCadastro)
class SolicitacaoCadastroAdmin(admin.ModelAdmin):
    list_display = ("nome", "cpf", "email", "perfil_solicitado", "setor_solicitado", "status", "data_solicitacao")
    list_filter = ("status", "perfil_solicitado", "setor_solicitado")
    search_fields = ("nome", "cpf", "email")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("item_nome", "item_descricao")
    search_fields = ("item_nome",)


@admin.register(Combo)
class ComboAdmin(admin.ModelAdmin):
    list_display = ("nome_combo", "item", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome_combo",)


@admin.register(ItemCombo)
class ItemComboAdmin(admin.ModelAdmin):
    list_display = ("tipo", "descricao", "item", "combo")
    search_fields = ("tipo", "descricao")


@admin.register(Competencia)
class CompetenciaAdmin(admin.ModelAdmin):
    list_display = ("combo", "ano", "mes", "status", "periodo")
    list_filter = ("status", "ano", "mes")
    search_fields = ("combo__nome_combo",)


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ("numero", "competencia", "setor")
    search_fields = ("numero",)


@admin.register(SetorCombo)
class SetorComboAdmin(admin.ModelAdmin):
    list_display = ("setor", "combo")
    list_filter = ("setor", "combo")


@admin.register(SetorComboItemCombo)
class SetorComboItemComboAdmin(admin.ModelAdmin):
    list_display = ("competencia", "valor", "setor", "item_combo", "setor_combo")
    list_filter = ("competencia", "setor", "item_combo")
    search_fields = ("observacao",)


# Registra o CustomUser com admin customizado
admin.site.register(CustomUser, CustomUserAdmin)
