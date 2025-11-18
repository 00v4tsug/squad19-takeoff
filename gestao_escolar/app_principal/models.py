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
        
    @property
    def valor_total(self):
        """Calcula o valor total do lançamento"""
        try:
            return self.valor_unitario
        except (TypeError, ValueError):
            return Decimal('0.00')

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
        """Calcula o valor total da folha"""
        try:
            return self.total_salarios + self.total_encargos
        except (TypeError, ValueError):
            return Decimal('0.00')

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
    total_gastos_operacionais = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_folha_pagamento = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_geral = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    quantidade_alunos = models.PositiveIntegerField(default=0)
    custo_por_aluno = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    data_calculo = models.DateTimeField(auto_now=True)
    data_atualizacao = models.DateTimeField(auto_now_add=True)
    
    # Novos campos para métricas
    percentual_folha = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    percentual_operacionais = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    eficiencia_custo = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # 0-100 score

    @classmethod
    def calcular_todos(cls):
        """Calcula dashboard para todas as competências abertas"""
        competencias_abertas = Competencia.objects.filter(aberta=True)
        total_criados = 0
        
        for competencia in competencias_abertas:
            instituicoes = Instituicao.objects.all()
            
            for instituicao in instituicoes:
                # Cálculos dos totais (mesma lógica do admin)
                gastos_operacionais = LancamentoGasto.objects.filter(
                    instituicao=instituicao,
                    competencia=competencia
                ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
                
                folha_pagamento = FolhaPagamento.objects.filter(
                    instituicao=instituicao,
                    competencia=competencia
                ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
                
                dados_alunos = DadosAlunos.objects.filter(
                    instituicao=instituicao,
                    competencia=competencia
                ).first()
                
                if dados_alunos:
                    quantidade_alunos = dados_alunos.quantidade_alunos
                    
                    dashboard, created = cls.objects.update_or_create(
                        instituicao=instituicao,
                        competencia=competencia,
                        defaults={
                            'total_gastos_operacionais': gastos_operacionais,
                            'total_folha_pagamento': folha_pagamento,
                            'quantidade_alunos': quantidade_alunos
                        }
                    )
                    
                    if created:
                        total_criados += 1
        
        return total_criados

    class Meta:
        unique_together = ['instituicao', 'competencia']
        verbose_name = "Dashboard - Custo por Aluno"
        verbose_name_plural = "Dashboards - Custo por Aluno"
        ordering = ['-competencia__ano', '-competencia__mes', 'instituicao__nome']

    def __str__(self):
        return f"Custo/Aluno - {self.instituicao} - {self.competencia}"

    def save(self, *args, **kwargs):
        # Cálculos automáticos
        self.total_geral = self.total_gastos_operacionais + self.total_folha_pagamento
        
        if self.quantidade_alunos > 0:
            self.custo_por_aluno = self.total_geral / self.quantidade_alunos
            
            # Calcular percentuais
            if self.total_geral > 0:
                self.percentual_folha = (self.total_folha_pagamento / self.total_geral) * 100
                self.percentual_operacionais = (self.total_gastos_operacionais / self.total_geral) * 100
                
                # Score de eficiência (quanto menor o custo por aluno, maior a eficiência)
                # Baseado em média histórica - ajuste conforme necessidade
                media_esperada = Decimal('500.00')  # Valor de referência
                if self.custo_por_aluno <= media_esperada:
                    self.eficiencia_custo = 100
                else:
                    self.eficiencia_custo = max(0, (media_esperada / self.custo_por_aluno) * 100)
        
        super().save(*args, **kwargs)

    @property
    def status_eficiencia(self):
        """Retorna status baseado no score de eficiência"""
        if self.eficiencia_custo >= 80:
            return "alta"
        elif self.eficiencia_custo >= 60:
            return "media"
        else:
            return "baixa"

    @property
    def variacao_mensal(self):
        """Calcula variação em relação ao mês anterior"""
        try:
            mes_anterior = Competencia.objects.filter(
                ano=self.competencia.ano,
                mes=self.competencia.mes - 1
            ).first()
            
            if mes_anterior:
                anterior = DashboardCustoAluno.objects.filter(
                    instituicao=self.instituicao,
                    competencia=mes_anterior
                ).first()
                
                if anterior and anterior.custo_por_aluno > 0:
                    variacao = ((self.custo_por_aluno - anterior.custo_por_aluno) / anterior.custo_por_aluno) * 100
                    return variacao
        except:
            pass
        return None
    

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