from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal

class UnidadeFederativa(models.Model):
    sigla = models.CharField(max_length=2, unique=True)
    nome = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.sigla} - {self.nome}"

class Municipio(models.Model):
    nome = models.CharField(max_length=100)
    uf = models.ForeignKey(UnidadeFederativa, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.nome} - {self.uf.sigla}"

class CustomUser(AbstractUser):
    class Cargos(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        GESTOR = "GESTOR", "Gestor"
        RH = "RH", "Recursos Humanos"
        RESPONSAVEL = "RESPONSAVEL", "Responsável Financeiro"

    cpf = models.CharField(max_length=11, unique=True, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    cargo = models.CharField(max_length=20, choices=Cargos.choices, default=Cargos.RESPONSAVEL)
    data_nascimento = models.DateField(blank=True, null=True)
    endereco = models.TextField(blank=True, null=True)
    municipio = models.ForeignKey(Municipio, on_delete=models.SET_NULL, null=True, blank=True)
    data_cadastro = models.DateTimeField(default=timezone.now)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_cargo_display()})"

class Instituicao(models.Model):
    TIPOS = [
        ('ESCOLA', 'Escola'),
        ('SECRETARIA', 'Secretaria de Educação'),
        ('DIRETORIA', 'Diretoria Regional'),
    ]
    
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='ESCOLA')
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE)
    endereco = models.TextField(blank=True, null=True)
    diretor = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="instituicoes_dirigidas")
    codigo_inep = models.CharField(max_length=8, blank=True, null=True, unique=True)
    responsavel = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name="instituicoes_responsavel", limit_choices_to={'cargo': 'RESPONSAVEL'})

    def __str__(self):
        return f"{self.nome} - {self.municipio}"

class CategoriaGasto(models.Model):
    codigo = models.CharField(max_length=10, unique=True)
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

class ItemGasto(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    categoria = models.ForeignKey(CategoriaGasto, on_delete=models.CASCADE)
    unidade_medida = models.CharField(max_length=20, default="R$")
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome

class Competencia(models.Model):
    MESES = [
        (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
        (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
        (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
    ]
    
    ano = models.PositiveIntegerField()
    mes = models.PositiveIntegerField(choices=MESES)
    aberta = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['ano', 'mes']
        ordering = ['-ano', '-mes']

    def __str__(self):
        return f"{self.mes:02d}/{self.ano}"

    @property
    def periodo(self):
        return f"{self.ano}-{self.mes:02d}"

class ComboGasto(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE)
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.nome} - {self.competencia}"

class ItemCombo(models.Model):
    combo = models.ForeignKey(ComboGasto, on_delete=models.CASCADE, related_name='itens')
    item_gasto = models.ForeignKey(ItemGasto, on_delete=models.CASCADE)
    valor_padrao = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    @property
    def valor_total_padrao(self):
        try:
            return self.valor_padrao
        except (TypeError, ValueError):
            return Decimal('0.00')

    def __str__(self):
        return f"{self.item_gasto} - {self.combo}"

# models.py - Modelo LancamentoGasto reformulado

class LancamentoGasto(models.Model):
    instituicao = models.ForeignKey(Instituicao, on_delete=models.CASCADE)
    competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE)
    item_gasto = models.ForeignKey(ItemGasto, on_delete=models.CASCADE)
    combo_origem = models.ForeignKey(ComboGasto, on_delete=models.SET_NULL, null=True, blank=True)
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    valor_total = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)], editable=False)
    observacao = models.TextField(blank=True, null=True)
    data_lancamento = models.DateTimeField(default=timezone.now)
    usuario_lancamento = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ['instituicao', 'competencia', 'item_gasto']
        verbose_name = "Lançamento de Gasto"
        verbose_name_plural = "Lançamentos de Gastos"
        ordering = ['-data_lancamento']

    def __str__(self):
        return f"{self.instituicao} - {self.item_gasto} - {self.competencia} - R$ {self.valor_total}"

    def save(self, *args, **kwargs):
        """Calcula automaticamente o valor_total antes de salvar"""
        # Calcula o valor total
        self.valor_total = self.valor_unitario * 1

        self.valor_total = Decimal(self.valor_total)
        
        # Arredonda para 2 casas decimais
        self.valor_total = self.valor_total.quantize(Decimal('0.01'))
        
        super().save(*args, **kwargs)

    @property
    def valor_total_formatado(self):
        """Retorna o valor total formatado como string"""
        return f"R$ {self.valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    @property
    def competencia_formatada(self):
        """Retorna a competência formatada"""
        return f"{self.competencia.mes:02d}/{self.competencia.ano}"

    def clean(self):
        """Validações adicionais"""
        from django.core.exceptions import ValidationError
        
        # Verifica se a competência está aberta
        if not self.competencia.aberta:
            raise ValidationError("Não é possível lançar em uma competência fechada.")
        
        # Verifica se a instituição pertence ao usuário (se já tem usuario_lancamento)
        if self.usuario_lancamento and self.instituicao.responsavel != self.usuario_lancamento:
            raise ValidationError("Você só pode lançar gastos para suas próprias instituições.")

class FolhaPagamento(models.Model):
    instituicao = models.ForeignKey(Instituicao, on_delete=models.CASCADE)
    competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE)
    total_salarios = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    total_encargos = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    observacao = models.TextField(blank=True, null=True)
    data_processamento = models.DateTimeField(default=timezone.now)
    usuario_processamento = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

    @property
    def valor_total(self):
        return self.total_salarios + self.total_encargos

    def __str__(self):
        return f"Folha - {self.instituicao} - {self.competencia}"

class DadosAlunos(models.Model):
    instituicao = models.ForeignKey(Instituicao, on_delete=models.CASCADE)
    competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE)
    quantidade_alunos = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    data_informacao = models.DateTimeField(default=timezone.now)
    usuario_informacao = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ['instituicao', 'competencia']

    def __str__(self):
        return f"Alunos - {self.instituicao} - {self.competencia}"

class DashboardCustoAluno(models.Model):
    instituicao = models.ForeignKey(Instituicao, on_delete=models.CASCADE)
    competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE)
    total_gastos_operacionais = models.DecimalField(max_digits=15, decimal_places=2)
    total_folha_pagamento = models.DecimalField(max_digits=15, decimal_places=2)
    total_geral = models.DecimalField(max_digits=15, decimal_places=2)
    quantidade_alunos = models.PositiveIntegerField()
    custo_por_aluno = models.DecimalField(max_digits=10, decimal_places=2)
    data_calculo = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['instituicao', 'competencia']
        verbose_name_plural = "Dashboards Custo por Aluno"

    def __str__(self):
        return f"Custo/Aluno - {self.instituicao} - {self.competencia}"

    def save(self, *args, **kwargs):
        self.total_geral = self.total_gastos_operacionais + self.total_folha_pagamento
        if self.quantidade_alunos > 0:
            self.custo_por_aluno = self.total_geral / self.quantidade_alunos
        else:
            self.custo_por_aluno = Decimal('0.00')
        super().save(*args, **kwargs)

class SolicitacaoCadastro(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('APROVADO', 'Aprovado'),
        ('REPROVADO', 'Reprovado'),
    ]
    
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=11)
    email = models.EmailField()
    telefone = models.CharField(max_length=20, blank=True, null=True)
    cargo_solicitado = models.CharField(max_length=20, choices=CustomUser.Cargos.choices)
    instituicao = models.ForeignKey(Instituicao, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    data_solicitacao = models.DateTimeField(default=timezone.now)
    data_resposta = models.DateTimeField(blank=True, null=True)
    admin_responsavel = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, 
                                        related_name="solicitacoes_aprovadas", limit_choices_to={'cargo': 'ADMIN'})
    observacao = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Solicitação - {self.nome} ({self.get_cargo_solicitado_display()})"