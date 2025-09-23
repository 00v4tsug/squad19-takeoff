from django.contrib.auth.models import AbstractUser
from django.db import models


class UnidadeFederativa(models.Model):
    sigla = models.CharField(max_length=2, unique=True)
    nome_unidade_federativa = models.CharField(max_length=100)

    def __str__(self):
        return self.nome_unidade_federativa


class Municipio(models.Model):
    nome_municipio = models.CharField(max_length=100)
    unidade_federativa = models.ForeignKey(UnidadeFederativa, on_delete=models.CASCADE)

    def __str__(self):
        return self.nome_municipio


class Perfil(models.Model):
    nome_perfil = models.CharField(max_length=50)
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome_perfil


class CustomUser(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        PROFESSOR = "PROFESSOR", "Professor"
        ALUNO = "ALUNO", "Aluno"

    cpf = models.CharField(max_length=11, unique=True, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.ALUNO)
    data_nascimento = models.DateField(blank=True, null=True)
    filiacao_1 = models.CharField(max_length=100, blank=True, null=True)
    filiacao_2 = models.CharField(max_length=100, blank=True, null=True)
    endereco = models.TextField(blank=True, null=True)
    perfil = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True)
    municipio = models.ForeignKey(Municipio, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class LogAcesso(models.Model):
    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    data_hora = models.DateTimeField(auto_now_add=True)


class Status(models.Model):
    tipo_status = models.CharField(max_length=50)
    descricao_status = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.tipo_status


class TipoSetor(models.Model):
    tipo_descricao = models.CharField(max_length=100)

    def __str__(self):
        return self.tipo_descricao


class Setor(models.Model):
    nome = models.CharField(max_length=100)
    tipo_setor = models.ForeignKey(TipoSetor, on_delete=models.CASCADE)
    setor_pai = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="sub_setores")
    municipio = models.ForeignKey(Municipio, on_delete=models.SET_NULL, null=True, blank=True)
    dados_endereco = models.TextField(blank=True, null=True)
    usuario = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.nome


class Solicitacao(models.Model):
    setor = models.ForeignKey(Setor, on_delete=models.CASCADE)
    descricao_solicitacao = models.TextField()
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, blank=True)
    admin_responsavel = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="solicitacoes_responsavel")
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_resposta = models.DateTimeField(blank=True, null=True)
    municipio = models.ForeignKey(Municipio, on_delete=models.SET_NULL, null=True, blank=True)
    nome = models.CharField(max_length=100, blank=True, null=True)


class SolicitacaoCadastro(models.Model):
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=11)
    email = models.EmailField()
    telefone = models.CharField(max_length=20, blank=True, null=True)
    perfil_solicitado = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, blank=True)
    setor_solicitado = models.ForeignKey(Setor, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, blank=True)
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_resposta = models.DateTimeField(blank=True, null=True)
    admin_responsavel = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="cadastros_responsavel")
    data_nascimento = models.DateField(blank=True, null=True)


class Item(models.Model):
    item_nome = models.CharField(max_length=100)
    item_descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.item_nome


class Combo(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    nome_combo = models.CharField(max_length=100)
    ativo = models.BooleanField(default=True)
    observacao = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome_combo


class ItemCombo(models.Model):
    tipo = models.CharField(max_length=50)
    descricao = models.TextField(blank=True, null=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    combo = models.ForeignKey(Combo, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.tipo} - {self.item}"


class Competencia(models.Model):
    combo = models.ForeignKey(Combo, on_delete=models.CASCADE)
    ano = models.DateField()
    mes = models.DateField()
    status = models.BooleanField(default=True)
    periodo = models.DateField()

    def __str__(self):
        return f"{self.ano}/{self.mes}"


class Aluno(models.Model):
    numero = models.IntegerField()
    competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE)
    setor = models.ForeignKey(Setor, on_delete=models.CASCADE)


class SetorCombo(models.Model):
    setor = models.ForeignKey(Setor, on_delete=models.CASCADE)
    combo = models.ForeignKey(Combo, on_delete=models.CASCADE)


class SetorComboItemCombo(models.Model):
    competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    setor = models.ForeignKey(Setor, on_delete=models.CASCADE)
    observacao = models.TextField(blank=True, null=True)
    item_combo = models.ForeignKey(ItemCombo, on_delete=models.CASCADE)
    setor_combo = models.ForeignKey(SetorCombo, on_delete=models.CASCADE)
