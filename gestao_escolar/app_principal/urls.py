from django.urls import path, include
from django.contrib import admin
from django.shortcuts import redirect
from rest_framework.routers import DefaultRouter
from . import views

# Importar admin personalizado
from .admin import admin_sistema

def redirect_to_admin(request):
    """Redireciona a raiz para o admin do sistema"""
    return redirect('/admin/')

# Router para APIs
router = DefaultRouter()

# Responsáveis
router.register(r'responsavel/instituicoes', views.ResponsavelInstituicaoViewSet, basename='responsavel-instituicoes')
router.register(r'responsavel/competencias', views.ResponsavelCompetenciaViewSet, basename='responsavel-competencias')
router.register(r'responsavel/combos', views.ResponsavelComboViewSet, basename='responsavel-combos')
router.register(r'responsavel/itens-gasto', views.ResponsavelItemGastoViewSet, basename='responsavel-itens-gasto')
router.register(r'responsavel/dados-alunos', views.ResponsavelDadosAlunosViewSet, basename='responsavel-dados-alunos')

# RH
router.register(r'rh/instituicoes', views.RHInstituicaoViewSet, basename='rh-instituicoes')
router.register(r'rh/competencias', views.RHCompetenciaViewSet, basename='rh-competencias')
router.register(r'rh/folha-pagamento', views.RHFolhaPagamentoViewSet, basename='rh-folha-pagamento')

router.register(r'responsavel/combos/(?P<combo_id>\d+)/lancamento', views.ComboLancamentoViewSet, basename='combo-lancamento')

urlpatterns = [
    # Redireciona raiz para admin
    path('', redirect_to_admin),
    
    # Admin personalizado do sistema
    path('admin/', admin_sistema.urls),
    
    # APIs
    path('api/', include(router.urls)),
    path('api/login/', views.LoginView.as_view(), name='api-login'),
    path('api/logout/', views.LogoutView.as_view(), name='api-logout'),
    path('api/solicitar-cadastro/', views.SolicitacaoCadastroView.as_view(), name='solicitar-cadastro'),
    path('api/dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('api/relatorios/', views.RelatoriosView.as_view(), name='relatorios'),
    path('api/calcular-custo-aluno/', views.CalcularCustoAlunoView.as_view(), name='calcular-custo-aluno'),
    
    # Login do REST Framework
    path('api-auth/', include('rest_framework.urls')),
]

# Configuração do admin padrão (backup)
admin.site.site_header = "Sistema de Gestão Educacional"
admin.site.site_title = "Admin"
admin.site.index_title = "Administração"