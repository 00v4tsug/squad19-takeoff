from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.db.models import Sum, Count
from django.utils import timezone
from .models import *
from django.db.models import Sum, Avg, Count
from django.contrib import messages
import json

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
    list_display = [
        'instituicao', 
        'competencia', 
        'custo_por_aluno_formatado',
        'total_geral_formatado',
        'quantidade_alunos',
        'status_eficiencia_display',
        'variacao_display',
        'data_calculo_formatada'
    ]
    
    list_filter = ['competencia', 'instituicao__municipio', 'instituicao__tipo']
    search_fields = ['instituicao__nome']
    readonly_fields = ['data_calculo', 'data_atualizacao', 'eficiencia_custo']
    actions = ['calcular_dashboard_action']
    
    change_list_template = 'admin/dashboard_change_list.html'

    def changelist_view(self, request, extra_context=None):
        # Calcular dashboard automaticamente se não houver dados recentes
        self.calcular_dashboard_automatico(request)
        
        # Preparar dados para os gráficos
        extra_context = extra_context or {}
        self.preparar_dados_dashboard(extra_context)
        
        return super().changelist_view(request, extra_context=extra_context)

    def calcular_dashboard_automatico(self, request):
        """Calcula o dashboard automaticamente se necessário"""
        # Verificar se existe alguma competência aberta
        competencias_abertas = Competencia.objects.filter(aberta=True)
        
        if not competencias_abertas.exists():
            messages.warning(request, "Não há competências abertas para cálculo.")
            return
        
        # Para cada competência aberta, calcular dashboard
        for competencia in competencias_abertas:
            # Verificar se já existe dashboard para esta competência
            dashboard_existente = DashboardCustoAluno.objects.filter(
                competencia=competencia
            ).exists()
            
            if not dashboard_existente:
                self.calcular_para_competencia(competencia, request)
    
    def calcular_para_competencia(self, competencia, request):
        """Calcula dashboard para uma competência específica"""
        try:
            instituicoes = Instituicao.objects.all()
            dashboards_criados = 0
            
            for instituicao in instituicoes:
                # Gastos operacionais
                gastos_operacionais = LancamentoGasto.objects.filter(
                    instituicao=instituicao,
                    competencia=competencia
                ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
                
                # Folha de pagamento
                folha_pagamento = FolhaPagamento.objects.filter(
                    instituicao=instituicao,
                    competencia=competencia
                ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
                
                # Dados de alunos
                dados_alunos = DadosAlunos.objects.filter(
                    instituicao=instituicao,
                    competencia=competencia
                ).first()
                
                if dados_alunos:
                    quantidade_alunos = dados_alunos.quantidade_alunos
                    
                    # Criar ou atualizar dashboard
                    dashboard, created = DashboardCustoAluno.objects.update_or_create(
                        instituicao=instituicao,
                        competencia=competencia,
                        defaults={
                            'total_gastos_operacionais': gastos_operacionais,
                            'total_folha_pagamento': folha_pagamento,
                            'quantidade_alunos': quantidade_alunos
                        }
                    )
                    
                    if created:
                        dashboards_criados += 1
            
            if dashboards_criados > 0:
                messages.success(
                    request, 
                    f'Dashboard calculado automaticamente para {competencia}. '
                    f'{dashboards_criados} instituições processadas.'
                )
                
        except Exception as e:
            messages.error(
                request, 
                f'Erro ao calcular dashboard automaticamente: {str(e)}'
            )

    def preparar_dados_dashboard(self, extra_context):
        """Prepara dados para os gráficos do dashboard"""
        # Última competência com dados
        ultima_competencia = Competencia.objects.filter(
            dashboardcustoaluno__isnull=False
        ).order_by('-ano', '-mes').first()
        
        if not ultima_competencia:
            # Se não há dados, usar última competência aberta
            ultima_competencia = Competencia.objects.filter(aberta=True).order_by('-ano', '-mes').first()
        
        if ultima_competencia:
            dados_ultima_competencia = DashboardCustoAluno.objects.filter(
                competencia=ultima_competencia
            )
            
            # Métricas gerais
            total_instituicoes = dados_ultima_competencia.count()
            media_custo_aluno = dados_ultima_competencia.aggregate(
                avg=Avg('custo_por_aluno')
            )['avg'] or Decimal('0.00')
            
            total_alunos = dados_ultima_competencia.aggregate(
                total=Sum('quantidade_alunos')
            )['total'] or 0
            
            total_investido = dados_ultima_competencia.aggregate(
                total=Sum('total_geral')
            )['total'] or Decimal('0.00')
            
            # Dados para gráficos
            grafico_custo_por_instituicao = list(
                dados_ultima_competencia.values('instituicao__nome').annotate(
                    custo=Avg('custo_por_aluno')
                ).order_by('-custo')[:10]
            )
            
            grafico_composicao_custos = {
                'folha': float(dados_ultima_competencia.aggregate(
                    total=Sum('total_folha_pagamento')
                )['total'] or 0),
                'operacionais': float(dados_ultima_competencia.aggregate(
                    total=Sum('total_gastos_operacionais')
                )['total'] or 0)
            }
            
            grafico_eficiencia = list(
                dados_ultima_competencia.values('instituicao__nome').annotate(
                    eficiencia=Avg('eficiencia_custo')
                ).order_by('-eficiencia')[:10]
            )
            
            # Evolução temporal (últimos 6 meses)
            ultimas_competencias = Competencia.objects.filter(
                dashboardcustoaluno__isnull=False
            ).distinct().order_by('-ano', '-mes')[:6]
            
            evolucao_temporal = []
            for comp in ultimas_competencias:
                dados_mes = DashboardCustoAluno.objects.filter(competencia=comp)
                media_mes = dados_mes.aggregate(avg=Avg('custo_por_aluno'))['avg'] or Decimal('0.00')
                evolucao_temporal.append({
                    'periodo': str(comp),
                    'media_custo': float(media_mes)
                })
            
            evolucao_temporal.reverse()
            
            extra_context.update({
                'ultima_competencia': ultima_competencia,
                'total_instituicoes': total_instituicoes,
                'media_custo_aluno': float(media_custo_aluno),
                'total_alunos': total_alunos,
                'total_investido': float(total_investido),
                'grafico_custo_por_instituicao': json.dumps(grafico_custo_por_instituicao),
                'grafico_composicao_custos': grafico_composicao_custos,
                'grafico_eficiencia': json.dumps(grafico_eficiencia),
                'evolucao_temporal': json.dumps(evolucao_temporal),
                'metricas_gerais': {
                    'instituicoes_eficientes': dados_ultima_competencia.filter(eficiencia_custo__gte=80).count(),
                    'instituicoes_medias': dados_ultima_competencia.filter(eficiencia_custo__gte=60, eficiencia_custo__lt=80).count(),
                    'instituicoes_baixas': dados_ultima_competencia.filter(eficiencia_custo__lt=60).count(),
                }
            })
        else:
            extra_context.update({
                'sem_dados': True
            })

    def calcular_dashboard_action(self, request, queryset):
        """Action para calcular dashboard manualmente"""
        competencias = Competencia.objects.filter(aberta=True)
        
        if not competencias.exists():
            self.message_user(request, "Não há competências abertas para cálculo.", messages.WARNING)
            return
        
        dashboards_criados = 0
        
        for competencia in competencias:
            dashboards_criados += self.calcular_para_competencia(competencia, request, silent=True)
        
        self.message_user(
            request, 
            f'Dashboard calculado para {competencias.count()} competências. '
            f'{dashboards_criados} registros criados/atualizados.', 
            messages.SUCCESS
        )
    
    calcular_dashboard_action.short_description = "Calcular dashboard para competências abertas"

    # Métodos de formatação (mantenha os anteriores)
    def custo_por_aluno_formatado(self, obj):
        return f"R$ {obj.custo_por_aluno:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    custo_por_aluno_formatado.short_description = 'Custo/Aluno'

    def total_geral_formatado(self, obj):
        return f"R$ {obj.total_geral:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    total_geral_formatado.short_description = 'Total Geral'

    def data_calculo_formatada(self, obj):
        return obj.data_calculo.strftime('%d/%m/%Y %H:%M')
    data_calculo_formatada.short_description = 'Data do Cálculo'

    def status_eficiencia_display(self, obj):
        color = {
            'alta': 'green',
            'media': 'orange', 
            'baixa': 'red'
        }.get(obj.status_eficiencia, 'gray')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">●</span> {}',
            color,
            obj.status_eficiencia.upper()
        )
    status_eficiencia_display.short_description = 'Eficiência'

    def variacao_display(self, obj):
        variacao = obj.variacao_mensal
        if variacao is not None:
            color = 'green' if variacao <= 0 else 'red'
            icon = '↘' if variacao <= 0 else '↗'
            return format_html(
                '<span style="color: {};">{} {:.1f}%</span>',
                color, icon, abs(variacao)
            )
        return '-'
    variacao_display.short_description = 'Variação'
    
    def calcular_para_competencia(self, competencia, request):
        """Calcula dashboard para uma competência específica"""
        try:
            instituicoes = Instituicao.objects.all()
            dashboards_criados = 0
            
            for instituicao in instituicoes:
                # Gastos operacionais - Soma manual dos valores totais
                lancamentos = LancamentoGasto.objects.filter(
                    instituicao=instituicao,
                    competencia=competencia
                )
                
                gastos_operacionais = Decimal('0.00')
                for lancamento in lancamentos:
                    gastos_operacionais += lancamento.valor_total
                
                # Folha de pagamento - Soma manual dos valores totais
                folhas = FolhaPagamento.objects.filter(
                    instituicao=instituicao,
                    competencia=competencia
                )
                
                folha_pagamento = Decimal('0.00')
                for folha in folhas:
                    folha_pagamento += folha.valor_total
                
                # Dados de alunos
                dados_alunos = DadosAlunos.objects.filter(
                    instituicao=instituicao,
                    competencia=competencia
                ).first()
                
                if dados_alunos:
                    quantidade_alunos = dados_alunos.quantidade_alunos
                    
                    # Criar ou atualizar dashboard
                    dashboard, created = DashboardCustoAluno.objects.update_or_create(
                        instituicao=instituicao,
                        competencia=competencia,
                        defaults={
                            'total_gastos_operacionais': gastos_operacionais,
                            'total_folha_pagamento': folha_pagamento,
                            'quantidade_alunos': quantidade_alunos
                        }
                    )
                    
                    if created:
                        dashboards_criados += 1
            
            if dashboards_criados > 0:
                messages.success(
                    request, 
                    f'Dashboard calculado automaticamente para {competencia}. '
                    f'{dashboards_criados} instituições processadas.'
                )
            else:
                messages.info(
                    request,
                    f'Dashboard já está atualizado para {competencia}.'
                )
                
        except Exception as e:
            messages.error(
                request, 
                f'Erro ao calcular dashboard automaticamente: {str(e)}'
            )

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