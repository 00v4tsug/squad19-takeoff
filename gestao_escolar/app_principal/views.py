from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.contrib.auth import login, logout
from .models import *
from .serializers import *
import json

# ========== PERMISSÕES PERSONALIZADAS ==========
class IsResponsavel(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.cargo == 'RESPONSAVEL'

class IsRH(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.cargo == 'RH'

class IsResponsavelOrRH(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.cargo in ['RESPONSAVEL', 'RH']

# ========== VIEWS PÚBLICAS ==========
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'cargo': user.cargo,
                'instituicoes_responsavel': [
                    {'id': inst.id, 'nome': inst.nome} 
                    for inst in user.instituicoes_responsavel.all()
                ] if user.cargo == 'RESPONSAVEL' else []
            }
            
            return Response({
                'user': user_data,
                'message': 'Login realizado com sucesso'
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'message': 'Logout realizado com sucesso'})

class SolicitacaoCadastroView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = SolicitacaoCadastroSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Solicitação de cadastro enviada com sucesso. Aguarde aprovação do administrador.'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ========== VIEWS PARA RESPONSÁVEIS ==========
class ResponsavelInstituicaoViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsResponsavel]
    serializer_class = InstituicaoSerializer
    
    def get_queryset(self):
        return Instituicao.objects.filter(responsavel=self.request.user)

class ResponsavelCompetenciaViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsResponsavel]
    queryset = Competencia.objects.filter(aberta=True)
    serializer_class = CompetenciaSerializer

class ResponsavelComboViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsResponsavel]
    serializer_class = ComboGastoSerializer

    def get_queryset(self):
        return ComboGasto.objects.filter(ativo=True, competencia__aberta=True)
    
# views.py - Substitua a ComboLancamentoViewSet completamente

class ComboLancamentoViewSet(viewsets.ViewSet):
    permission_classes = [IsResponsavel]
    
    def create(self, request, combo_id=None):
        """
        POST /api/responsavel/combos/2/lancamento/
        Cria lançamentos em lote para todos os itens do combo
        """
        try:
            combo = ComboGasto.objects.get(id=combo_id, ativo=True)
            
            # Se não veio dados no body, criar payload automático com valores padrão
            if not request.data:
                return self._criar_payload_automatico(combo, request.user)
            
            # Processar o lançamento em lote
            serializer = LancamentoComboLoteSerializer(
                data=request.data,
                context={
                    'request': request,
                    'combo_id': combo_id
                }
            )
            
            if serializer.is_valid():
                result = serializer.save()
                
                # Serializar os lançamentos criados
                lancamentos_serializer = LancamentoGastoSerializer(
                    result['lancamentos_criados'], 
                    many=True
                )
                
                return Response({
                    'success': True,
                    'message': f'{result["total_criado"]} lançamentos criados com sucesso para o combo {result["combo"]}',
                    'detalhes': {
                        'combo': result['combo'],
                        'competencia': result['competencia'],
                        'total_itens_processados': result['total_criado']
                    },
                    'lancamentos': lancamentos_serializer.data
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'success': False,
                'error': 'Dados inválidos',
                'detalhes': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
                
        except ComboGasto.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Combo não encontrado ou inativo'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def _criar_payload_automatico(self, combo, user):
        """Cria payload automático com valores padrão do combo"""
        instituicoes = Instituicao.objects.filter(responsavel=user)
        itens_combo = combo.itens.select_related('item_gasto', 'item_gasto__categoria').all()
        
        # Se só tem uma instituição, usa ela automaticamente
        instituicao_id = instituicoes.first().id if instituicoes.count() == 1 else None
        
        payload_sugerido = {
            'instituicao': instituicao_id,
            'observacao_geral': f'Lançamento automático do combo {combo.nome}',
            'itens': [
                {
                    'item_gasto_id': item.item_gasto.id,
                    'item_gasto_nome': item.item_gasto.nome,
                    'categoria_nome': item.item_gasto.categoria.nome,
                    'unidade_medida': item.item_gasto.unidade_medida,
                    'valor_padrao': str(item.valor_padrao),
                    'quantidade': 1,
                    'valor_unitario': str(item.valor_padrao),
                    'observacao': f'{item.item_gasto.nome} - {combo.nome}'
                }
                for item in itens_combo
            ]
        }
        
        return Response({
            'success': True,
            'message': 'Use este payload para criar os lançamentos',
            'instrucoes': 'Envie um POST com os dados abaixo. Ajuste quantidades e valores conforme necessário.',
            'combo_info': {
                'id': combo.id,
                'nome': combo.nome,
                'competencia': str(combo.competencia),
                'total_itens': itens_combo.count()
            },
            'instituicoes_disponiveis': [
                {'id': inst.id, 'nome': inst.nome} 
                for inst in instituicoes
            ],
            'payload_sugerido': payload_sugerido
        }, status=status.HTTP_200_OK)

    def list(self, request, combo_id=None):
        """
        GET /api/responsavel/combos/2/lancamento/
        Lista lançamentos existentes e informações do combo
        """
        try:
            combo = ComboGasto.objects.get(id=combo_id, ativo=True)
            
            # Lançamentos existentes
            lancamentos = LancamentoGasto.objects.filter(
                combo_origem_id=combo_id,
                instituicao__responsavel=request.user
            ).select_related('instituicao', 'competencia', 'item_gasto')
            
            # Itens do combo
            itens_combo = combo.itens.select_related('item_gasto', 'item_gasto__categoria').all()
            
            # Instituições do usuário
            instituicoes = Instituicao.objects.filter(responsavel=request.user)
            
            # Preparar dados para criação
            itens_para_lancar = []
            for item in itens_combo:
                # Verificar se já existe lançamento para cada instituição
                lancamento_existente = lancamentos.filter(item_gasto=item.item_gasto).first()
                
                itens_para_lancar.append({
                    'item_gasto_id': item.item_gasto.id,
                    'item_gasto_nome': item.item_gasto.nome,
                    'categoria_nome': item.item_gasto.categoria.nome,
                    'unidade_medida': item.item_gasto.unidade_medida,
                    'valor_padrao': str(item.valor_padrao),
                    'quantidade_sugerida': 1,
                    'valor_unitario_sugerido': str(item.valor_padrao),
                    'ja_lancado': lancamento_existente is not None,
                    'lancamento_existente_id': lancamento_existente.id if lancamento_existente else None
                })
            
            return Response({
                'combo': {
                    'id': combo.id,
                    'nome': combo.nome,
                    'descricao': combo.descricao,
                    'competencia': str(combo.competencia),
                    'data_criacao': combo.data_criacao
                },
                'instituicoes_disponiveis': [
                    {'id': inst.id, 'nome': inst.nome} 
                    for inst in instituicoes
                ],
                'itens_do_combo': itens_para_lancar,
                'lancamentos_existentes': LancamentoGastoSerializer(lancamentos, many=True).data,
                'estatisticas': {
                    'total_itens_combo': itens_combo.count(),
                    'total_lancamentos_existentes': lancamentos.count(),
                    'total_para_lancar': len([item for item in itens_para_lancar if not item['ja_lancado']])
                }
            })
            
        except ComboGasto.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Combo não encontrado ou inativo'
            }, status=status.HTTP_404_NOT_FOUND)
            
class ResponsavelItemGastoViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsResponsavel]
    queryset = ItemGasto.objects.filter(ativo=True)
    serializer_class = ItemGastoSerializer

class ResponsavelDadosAlunosViewSet(viewsets.ModelViewSet):
    permission_classes = [IsResponsavel]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update']:
            return DadosAlunosCreateSerializer
        return DadosAlunosSerializer
    
    def get_queryset(self):
        return DadosAlunos.objects.filter(
            instituicao__responsavel=self.request.user
        ).select_related('instituicao', 'competencia')
    
    def perform_create(self, serializer):
        serializer.save(usuario_informacao=self.request.user)

# ========== VIEWS PARA RH ==========
class RHInstituicaoViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsRH]
    queryset = Instituicao.objects.all()
    serializer_class = InstituicaoSerializer

class RHCompetenciaViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsRH]
    queryset = Competencia.objects.filter(aberta=True)
    serializer_class = CompetenciaSerializer

class RHFolhaPagamentoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsRH]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update']:
            return FolhaPagamentoCreateSerializer
        return FolhaPagamentoSerializer
    
    def get_queryset(self):
        return FolhaPagamento.objects.all().select_related('instituicao', 'competencia')
    
    def perform_create(self, serializer):
        serializer.save(usuario_processamento=self.request.user)

# ========== VIEWS PARA DASHBOARD E RELATÓRIOS ==========
class DashboardView(APIView):
    permission_classes = [IsResponsavelOrRH]
    
    def get(self, request):
        user = request.user
        instituicao_id = request.query_params.get('instituicao_id')
        competencia_id = request.query_params.get('competencia_id')
        
        # Filtros baseados no usuário
        if user.cargo == 'RESPONSAVEL':
            instituicoes = Instituicao.objects.filter(responsavel=user)
        else:  # RH
            instituicoes = Instituicao.objects.all()
        
        if instituicao_id:
            instituicoes = instituicoes.filter(id=instituicao_id)
        
        # Buscar dados do dashboard
        dashboards = DashboardCustoAluno.objects.filter(
            instituicao__in=instituicoes
        )
        
        if competencia_id:
            dashboards = dashboards.filter(competencia_id=competencia_id)
        else:
            # Última competência com dados
            ultima_competencia = Competencia.objects.filter(
                dashboardcustoaluno__in=dashboards
            ).order_by('-ano', '-mes').first()
            
            if ultima_competencia:
                dashboards = dashboards.filter(competencia=ultima_competencia)
        
        serializer = DashboardCustoAlunoSerializer(dashboards, many=True)
        
        return Response({
            'dashboards': serializer.data,
            'total_instituicoes': instituicoes.count(),
            'periodo_selecionado': dashboards.first().competencia.periodo if dashboards.exists() else 'N/A'
        })

class RelatoriosView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = RelatorioCustoSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            # Calcular totais baseado nos filtros
            filtros = Q()
            
            if data.get('instituicao_id'):
                filtros &= Q(instituicao_id=data['instituicao_id'])
            if data.get('competencia_id'):
                filtros &= Q(competencia_id=data['competencia_id'])
            if data.get('ano'):
                filtros &= Q(competencia__ano=data['ano'])
            
            # Gastos operacionais
            gastos_operacionais = LancamentoGasto.objects.filter(filtros).aggregate(
                total=Sum('valor_total')
            )['total'] or 0
            
            # Folha de pagamento
            folha_pagamento = FolhaPagamento.objects.filter(filtros).aggregate(
                total=Sum('valor_total')
            )['total'] or 0
            
            # Dados de alunos (média)
            dados_alunos = DadosAlunos.objects.filter(filtros).aggregate(
                media=Sum('quantidade_alunos') / Count('id')
            )['media'] or 0
            
            total_geral = gastos_operacionais + folha_pagamento
            custo_por_aluno = total_geral / dados_alunos if dados_alunos > 0 else 0
            
            return Response({
                'total_gastos_operacionais': gastos_operacionais,
                'total_folha_pagamento': folha_pagamento,
                'total_geral': total_geral,
                'quantidade_alunos': dados_alunos,
                'custo_por_aluno': custo_por_aluno
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ========== VIEW PARA CÁLCULO AUTOMÁTICO ==========
class CalcularCustoAlunoView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """
        Calcula e atualiza o custo por aluno para todas as instituições de uma competência
        """
        competencia_id = request.data.get('competencia_id')
        
        if not competencia_id:
            return Response({'error': 'competencia_id é obrigatório'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            competencia = Competencia.objects.get(id=competencia_id)
            instituicoes = Instituicao.objects.all()
            
            resultados = []
            
            for instituicao in instituicoes:
                # Gastos operacionais da instituição na competência
                gastos_operacionais = LancamentoGasto.objects.filter(
                    instituicao=instituicao,
                    competencia=competencia
                ).aggregate(total=Sum('valor_total'))['total'] or 0
                
                # Folha de pagamento da instituição na competência
                folha_pagamento = FolhaPagamento.objects.filter(
                    instituicao=instituicao,
                    competencia=competencia
                ).aggregate(total=Sum('valor_total'))['total'] or 0
                
                # Dados de alunos da instituição na competência
                dados_alunos = DadosAlunos.objects.filter(
                    instituicao=instituicao,
                    competencia=competencia
                ).first()
                
                if dados_alunos:
                    quantidade_alunos = dados_alunos.quantidade_alunos
                    total_geral = gastos_operacionais + folha_pagamento
                    custo_por_aluno = total_geral / quantidade_alunos if quantidade_alunos > 0 else 0
                    
                    # Criar ou atualizar dashboard
                    dashboard, created = DashboardCustoAluno.objects.update_or_create(
                        instituicao=instituicao,
                        competencia=competencia,
                        defaults={
                            'total_gastos_operacionais': gastos_operacionais,
                            'total_folha_pagamento': folha_pagamento,
                            'quantidade_alunos': quantidade_alunos,
                            'custo_por_aluno': custo_por_aluno
                        }
                    )
                    
                    resultados.append({
                        'instituicao': instituicao.nome,
                        'competencia': competencia.periodo,
                        'total_gastos_operacionais': gastos_operacionais,
                        'total_folha_pagamento': folha_pagamento,
                        'total_geral': total_geral,
                        'quantidade_alunos': quantidade_alunos,
                        'custo_por_aluno': custo_por_aluno,
                        'status': 'Atualizado' if not created else 'Criado'
                    })
            
            return Response({
                'message': f'Cálculo concluído para {len(resultados)} instituições',
                'resultados': resultados
            })
            
        except Competencia.DoesNotExist:
            return Response({'error': 'Competência não encontrada'}, status=status.HTTP_404_NOT_FOUND)