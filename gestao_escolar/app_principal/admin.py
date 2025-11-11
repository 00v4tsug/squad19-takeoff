from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.db.models import Sum, Count
from django.utils import timezone
from .models import *

class AdminSistemaSite(admin.AdminSite):
    site_header = "🏫 Sistema de Gestão Educacional - Painel Administrativo"
    site_title = "Painel do Administrador"
    index_title = "Dashboard Principal"
    
    def index(self, request, extra_context=None):
        # Estatísticas para o dashboard
        if request.user.is_authenticated and hasattr(request.user, 'cargo') and request.user.cargo == 'ADMIN':
            stats = {
                'total_instituicoes': Instituicao.objects.count(),
                'solicitacoes_pendentes': SolicitacaoCadastro.objects.filter(status='PENDENTE').count(),
                'competencias_abertas': Competencia.objects.filter(aberta=True).count(),
                'combos_ativos': ComboGasto.objects.filter(ativo=True).count(),
                'ultimas_solicitacoes': SolicitacaoCadastro.objects.filter(status='PENDENTE').order_by('-data_solicitacao')[:5],
            }
            extra_context = extra_context or {}
            extra_context.update(stats)
        
        return super().index(request, extra_context=extra_context)

admin_sistema = AdminSistemaSite(name='admin_sistema')

# ========== INLINES ==========
class ItemComboInline(admin.TabularInline):
    model = ItemCombo
    extra = 1
    fields = ('item_gasto', 'valor_padrao', 'valor_total_padrao_display')
    readonly_fields = ('valor_total_padrao_display',)
    
    def valor_total_padrao_display(self, obj):
        if obj.valor_padrao is None:
            return "—"
        try:
            total = obj.valor_padrao * getattr(obj, 'quantidade_padrao', 1)
            return f"R$ {total:.2f}"
        except TypeError:
            return "—"

# ========== MODEL ADMINS CORRIGIDOS ==========
@admin.register(CustomUser, site=admin_sistema)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'get_full_name', 'cargo_badge', 'municipio', 'status_badge', 'ativo')
    list_filter = ('cargo', 'ativo', 'municipio')
    list_editable = ('ativo',)  # ✅ CORRIGIDO: campo 'ativo' está no list_display
    fieldsets = UserAdmin.fieldsets + (
        ('Informações do Sistema', {
            'fields': ('cargo', 'municipio', 'ativo')
        }),
        ('Informações Pessoais', {
            'fields': ('cpf', 'telefone', 'data_nascimento', 'endereco')
        }),
    )
    
    def cargo_badge(self, obj):
        cores = {
            'ADMIN': '#e74c3c',
            'GESTOR': '#3498db', 
            'RH': '#9b59b6',
            'RESPONSAVEL': '#2ecc71'
        }
        cor = cores.get(obj.cargo, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">{}</span>',
            cor, obj.get_cargo_display()
        )
    cargo_badge.short_description = 'Cargo'

    def status_badge(self, obj):
        if obj.ativo:
            return format_html('<span style="color: green; font-weight: bold;">● ATIVO</span>')
        return format_html('<span style="color: red; font-weight: bold;">● INATIVO</span>')
    status_badge.short_description = 'Status Visual'

@admin.register(Instituicao, site=admin_sistema)
class InstituicaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'municipio', 'diretor', 'responsavel', 'quantidade_alunos_atual')
    list_filter = ('tipo', 'municipio__uf')
    search_fields = ('nome', 'codigo_inep')
    
    def quantidade_alunos_atual(self, obj):
        ultimo_dado = DadosAlunos.objects.filter(instituicao=obj).order_by('-competencia__ano', '-competencia__mes').first()
        return ultimo_dado.quantidade_alunos if ultimo_dado else 0
    quantidade_alunos_atual.short_description = 'Alunos (Atual)'

@admin.register(Competencia, site=admin_sistema)
class CompetenciaAdmin(admin.ModelAdmin):
    list_display = ('ano', 'mes_display', 'status_badge', 'total_lancamentos', 'periodo', 'aberta')
    list_filter = ('ano', 'mes')
    list_editable = ('aberta',)
    ordering = ('-ano', '-mes')
    
    def mes_display(self, obj):
        return obj.get_mes_display()
    mes_display.short_description = 'Mês'

    def status_badge(self, obj):
        if obj.aberta:
            return format_html('<span style="color: green; font-weight: bold;">● ABERTA</span>')
        return format_html('<span style="color: red; font-weight: bold;">● FECHADA</span>')
    status_badge.short_description = 'Status'

    def total_lancamentos(self, obj):
        count = LancamentoGasto.objects.filter(competencia=obj).count()
        return format_html(f'<b>{count}</b> lançamentos')
    total_lancamentos.short_description = 'Lançamentos'

@admin.register(ComboGasto, site=admin_sistema)
class ComboGastoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'competencia', 'status_badge', 'total_combo', 'data_criacao', 'ativo')
    list_filter = ('competencia', 'ativo')
    search_fields = ('nome', 'descricao')
    list_editable = ('ativo',)  # ✅ CORRIGIDO: campo 'ativo' está no list_display
    inlines = [ItemComboInline]
    
    def status_badge(self, obj):
        if obj.ativo:
            return format_html('<span style="color: green;">● ATIVO</span>')
        return format_html('<span style="color: red;">● INATIVO</span>')
    status_badge.short_description = 'Status'

    def total_combo(self, obj):
        total = sum(item.valor_total_padrao for item in obj.itens.all())
        return format_html(f'<b>R$ {total:,.2f}</b>')
    total_combo.short_description = 'Valor Total'

@admin.register(ItemGasto, site=admin_sistema)
class ItemGastoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'unidade_medida', 'status_badge', 'ativo')
    list_filter = ('categoria', 'ativo')
    search_fields = ('nome', 'descricao')
    list_editable = ('ativo',)  # ✅ CORRIGIDO: campo 'ativo' está no list_display
    
    def status_badge(self, obj):
        if obj.ativo:
            return format_html('<span style="color: green;">● ATIVO</span>')
        return format_html('<span style="color: red;">● INATIVO</span>')
    status_badge.short_description = 'Status'

@admin.register(SolicitacaoCadastro, site=admin_sistema)
class SolicitacaoCadastroAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cpf', 'email', 'cargo_solicitado_badge', 'instituicao', 'status_badge', 'status', 'data_solicitacao')
    list_filter = ('cargo_solicitado', 'status', 'instituicao')
    search_fields = ('nome', 'cpf', 'email')
    readonly_fields = ('data_solicitacao', 'data_resposta')
    list_editable = ('status',)  # ✅ CORRIGIDO: campo 'status' está no list_display
    actions = ['aprovar_solicitacoes', 'reprovar_solicitacoes']
    
    def cargo_solicitado_badge(self, obj):
        cores = {
            'GESTOR': '#3498db',
            'RH': '#9b59b6',
            'RESPONSAVEL': '#2ecc71'
        }
        cor = cores.get(obj.cargo_solicitado, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            cor, obj.get_cargo_solicitado_display()
        )
    cargo_solicitado_badge.short_description = 'Cargo Solicitado'

    def status_badge(self, obj):
        if obj.status == 'PENDENTE':
            return format_html('<span style="color: orange; font-weight: bold;">● PENDENTE</span>')
        elif obj.status == 'APROVADO':
            return format_html('<span style="color: green; font-weight: bold;">● APROVADO</span>')
        return format_html('<span style="color: red; font-weight: bold;">● REPROVADO</span>')
    status_badge.short_description = 'Status Visual'

    def aprovar_solicitacoes(self, request, queryset):
        solicitacoes = queryset.filter(status='PENDENTE')
        for solicitacao in solicitacoes:
            user = CustomUser.objects.create_user(
                username=solicitacao.cpf,
                email=solicitacao.email,
                first_name=solicitacao.nome,
                cpf=solicitacao.cpf,
                telefone=solicitacao.telefone,
                cargo=solicitacao.cargo_solicitado,
                ativo=True
            )
            user.set_password(solicitacao.cpf)
            user.save()
            
            if solicitacao.cargo_solicitado == 'RESPONSAVEL' and solicitacao.instituicao:
                solicitacao.instituicao.responsavel = user
                solicitacao.instituicao.save()
            
            solicitacao.status = 'APROVADO'
            solicitacao.admin_responsavel = request.user
            solicitacao.data_resposta = timezone.now()
            solicitacao.save()
        
        self.message_user(request, f"{solicitacoes.count()} solicitação(ões) aprovada(s) com sucesso!")
    aprovar_solicitacoes.short_description = "✅ Aprovar solicitações selecionadas"

    def reprovar_solicitacoes(self, request, queryset):
        updated = queryset.filter(status='PENDENTE').update(
            status='REPROVADO',
            admin_responsavel=request.user,
            data_resposta=timezone.now()
        )
        self.message_user(request, f"{updated} solicitação(ões) reprovada(s) com sucesso!")
    reprovar_solicitacoes.short_description = "❌ Reprovar solicitações selecionadas"

@admin.register(DashboardCustoAluno, site=admin_sistema)
class DashboardCustoAlunoAdmin(admin.ModelAdmin):
    list_display = ('instituicao', 'competencia', 'total_geral_format', 'quantidade_alunos', 'custo_por_aluno_format', 'data_calculo')
    list_filter = ('competencia', 'instituicao__municipio__uf')
    readonly_fields = ('data_calculo',)
    
    def total_geral_format(self, obj):
        return format_html(f'<b style="color: #e74c3c;">R$ {obj.total_geral:,.2f}</b>')
    total_geral_format.short_description = 'Total Geral'

    def custo_por_aluno_format(self, obj):
        return format_html(f'<b style="color: #27ae60;">R$ {obj.custo_por_aluno:,.2f}</b>')
    custo_por_aluno_format.short_description = 'Custo por Aluno'

    def has_add_permission(self, request):
        return False

# ========== MODELOS BÁSICOS ==========
@admin.register(UnidadeFederativa, site=admin_sistema)
class UnidadeFederativaAdmin(admin.ModelAdmin):
    list_display = ('sigla', 'nome')
    search_fields = ('sigla', 'nome')

@admin.register(Municipio, site=admin_sistema)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'uf')
    list_filter = ('uf',)
    search_fields = ('nome',)

@admin.register(CategoriaGasto, site=admin_sistema)
class CategoriaGastoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nome', 'descricao')
    search_fields = ('codigo', 'nome')


@admin.register(DadosAlunos, site=admin_sistema)
class DadosAlunosAdmin(admin.ModelAdmin):
    list_display = ('instituicao', 'competencia', 'quantidade_alunos', 'data_informacao')
    list_filter = ('competencia', 'instituicao')