from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import *

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if user.is_active and user.ativo:
                    data['user'] = user
                else:
                    raise serializers.ValidationError('Usuário desativado.')
            else:
                raise serializers.ValidationError('Credenciais inválidas.')
        else:
            raise serializers.ValidationError('Deve incluir username e password.')

        return data

class InstituicaoSerializer(serializers.ModelSerializer):
    municipio_nome = serializers.CharField(source='municipio.nome', read_only=True)
    uf_sigla = serializers.CharField(source='municipio.uf.sigla', read_only=True)
    
    class Meta:
        model = Instituicao
        fields = ['id', 'nome', 'tipo', 'municipio', 'municipio_nome', 'uf_sigla', 'codigo_inep']

class CompetenciaSerializer(serializers.ModelSerializer):
    periodo = serializers.CharField(read_only=True)
    mes_nome = serializers.CharField(source='get_mes_display', read_only=True)
    
    class Meta:
        model = Competencia
        fields = ['id', 'ano', 'mes', 'mes_nome', 'aberta', 'periodo']

class ItemGastoSerializer(serializers.ModelSerializer):
    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)
    
    class Meta:
        model = ItemGasto
        fields = ['id', 'nome', 'descricao', 'categoria', 'categoria_nome', 'unidade_medida']

class ComboGastoSerializer(serializers.ModelSerializer):
    competencia_periodo = serializers.CharField(source='competencia.periodo', read_only=True)
    total_combo = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = ComboGasto
        fields = ['id', 'nome', 'descricao', 'competencia', 'competencia_periodo', 'ativo', 'total_combo']

class ItemComboSerializer(serializers.ModelSerializer):
    item_gasto_nome = serializers.CharField(source='item_gasto.nome', read_only=True)
    valor_total_padrao = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = ItemCombo
        fields = ['id', 'combo', 'item_gasto', 'item_gasto_nome', 'valor_padrao', 'valor_total_padrao']

class LancamentoGastoSerializer(serializers.ModelSerializer):
    instituicao_nome = serializers.CharField(source='instituicao.nome', read_only=True)
    item_gasto_nome = serializers.CharField(source='item_gasto.nome', read_only=True)
    item_gasto_unidade = serializers.CharField(source='item_gasto.unidade_medida', read_only=True)
    categoria_nome = serializers.CharField(source='item_gasto.categoria.nome', read_only=True)
    competencia_periodo = serializers.CharField(source='competencia.periodo', read_only=True)
    usuario_lancamento_nome = serializers.CharField(source='usuario_lancamento.get_full_name', read_only=True)
    combo_origem_nome = serializers.CharField(source='combo_origem.nome', read_only=True, allow_null=True)
    
    class Meta:
        model = LancamentoGasto
        fields = [
            'id', 'instituicao', 'instituicao_nome', 'competencia', 'competencia_periodo',
            'item_gasto', 'item_gasto_nome', 'item_gasto_unidade', 'categoria_nome',
            'combo_origem', 'combo_origem_nome', 'valor_unitario',
            'valor_total', 'observacao', 'data_lancamento', 'usuario_lancamento',
            'usuario_lancamento_nome'
        ]
        read_only_fields = ['data_lancamento', 'valor_total', 'usuario_lancamento']

class LancamentoGastoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LancamentoGasto
        fields = [
            'instituicao', 'competencia', 'item_gasto', 'combo_origem',
            'quantidade', 'valor_unitario', 'observacao'
        ]
    
    def validate(self, data):
        # Verificar se a competência está aberta
        if not data['competencia'].aberta:
            raise serializers.ValidationError("Esta competência está fechada para lançamentos.")
        
        # Verificar se já existe lançamento para o mesmo item na mesma competência e instituição
        if LancamentoGasto.objects.filter(
            instituicao=data['instituicao'],
            competencia=data['competencia'],
            item_gasto=data['item_gasto']
        ).exists():
            raise serializers.ValidationError(
                "Já existe um lançamento para este item na mesma competência e instituição."
            )
        
        return data

class LancamentoComboSerializer(serializers.ModelSerializer):
    item_gasto_nome = serializers.CharField(source='item_gasto.nome', read_only=True)
    unidade_medida = serializers.CharField(source='item_gasto.unidade_medida', read_only=True)
    
    class Meta:
        model = LancamentoGasto
        fields = [
            'id', 'instituicao', 'competencia', 'item_gasto', 'item_gasto_nome',
            'unidade_medida', 'quantidade', 'valor_unitario', 'valor_total',
            'observacao', 'data_lancamento'
        ]
        read_only_fields = ['data_lancamento', 'valor_total']

# serializers.py - Atualize o serializer principal

class LancamentoComboLoteSerializer(serializers.Serializer):
    instituicao = serializers.PrimaryKeyRelatedField(
        queryset=Instituicao.objects.all(),
        required=True
    )
    observacao_geral = serializers.CharField(required=False, allow_blank=True, default="")
    itens = serializers.ListField(
        child=serializers.DictField(),
        required=True
    )
    
    def validate_instituicao(self, value):
        user = self.context['request'].user
        if not Instituicao.objects.filter(id=value.id, responsavel=user).exists():
            raise serializers.ValidationError("Você não tem permissão para esta instituição")
        return value
    
    def validate_itens(self, value):
        if not value:
            raise serializers.ValidationError("Pelo menos um item deve ser informado")
        
        for item in value:
            required_fields = ['item_gasto_id', 'valor_unitario']
            for field in required_fields:
                if field not in item:
                    raise serializers.ValidationError(f"Campo '{field}' é obrigatório para cada item")
            
            # Validar tipos
            try:
                float(item['valor_unitario'])
            except (TypeError, ValueError):
                raise serializers.ValidationError("Quantidade e valor_unitario devem ser números válidos")
        
        return value
    
    def create(self, validated_data):
        combo_id = self.context['combo_id']
        user = self.context['request'].user
        
        try:
            combo = ComboGasto.objects.get(id=combo_id)
            instituicao = validated_data['instituicao']
            observacao_geral = validated_data.get('observacao_geral', '')
            
            lancamentos_criados = []
            itens_combo_ids = set(combo.itens.values_list('item_gasto_id', flat=True))
            
            for item_data in validated_data['itens']:
                item_gasto_id = item_data['item_gasto_id']
                valor_unitario = item_data['valor_unitario']
                observacao_item = item_data.get('observacao', '')
                
                # Verificar se o item pertence ao combo
                if item_gasto_id not in itens_combo_ids:
                    continue
                
                # Verificar se já existe lançamento
                if LancamentoGasto.objects.filter(
                    instituicao=instituicao,
                    competencia=combo.competencia,
                    item_gasto_id=item_gasto_id
                ).exists():
                    continue
                
                # Criar observação combinada
                observacao_final = f"Combo: {combo.nome}"
                if observacao_geral:
                    observacao_final += f" | {observacao_geral}"
                if observacao_item:
                    observacao_final += f" | {observacao_item}"
                
                # Criar lançamento
                lancamento = LancamentoGasto.objects.create(
                    instituicao=instituicao,
                    competencia=combo.competencia,
                    item_gasto_id=item_gasto_id,
                    combo_origem=combo,
                    valor_unitario=valor_unitario,
                    observacao=observacao_final,
                    usuario_lancamento=user
                )
                lancamentos_criados.append(lancamento)
            
            return {
                'lancamentos_criados': lancamentos_criados,
                'total_criado': len(lancamentos_criados),
                'combo': combo.nome,
                'competencia': str(combo.competencia)
            }
            
        except ComboGasto.DoesNotExist:
            raise serializers.ValidationError("Combo não encontrado")
        
class ComboLancamentoSerializer(serializers.ModelSerializer):
    itens_combo = ItemComboSerializer(many=True, read_only=True, source='itens')
    competencia_info = CompetenciaSerializer(source='competencia', read_only=True)
    
    class Meta:
        model = ComboGasto
        fields = [
            'id', 'nome', 'descricao', 'competencia', 'competencia_info',
            'ativo', 'data_criacao', 'itens_combo'
        ]

# ========== SERIALIZERS PARA FOLHA DE PAGAMENTO ==========
class FolhaPagamentoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FolhaPagamento
        fields = ['instituicao', 'competencia', 'total_salarios', 'total_encargos', 'observacao']
    
    def validate(self, data):
        competencia = data.get('competencia')
        if competencia and not competencia.aberta:
            raise serializers.ValidationError('Esta competência está fechada para lançamentos.')
        
        user = self.context['request'].user
        if user.cargo != 'RH':
            raise serializers.ValidationError('Apenas usuários do RH podem lançar folha de pagamento.')
        
        return data

    def create(self, validated_data):
        validated_data['usuario_processamento'] = self.context['request'].user
        return super().create(validated_data)

class FolhaPagamentoSerializer(serializers.ModelSerializer):
    instituicao_nome = serializers.CharField(source='instituicao.nome', read_only=True)
    competencia_periodo = serializers.CharField(source='competencia.periodo', read_only=True)
    valor_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = FolhaPagamento
        fields = '__all__'

# ========== SERIALIZERS PARA DADOS DE ALUNOS ==========
class DadosAlunosCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DadosAlunos
        fields = ['instituicao', 'competencia', 'quantidade_alunos']
    
    def validate(self, data):
        user = self.context['request'].user
        instituicao = data.get('instituicao')
        
        if user.cargo != 'RESPONSAVEL' or user != instituicao.responsavel:
            raise serializers.ValidationError('Você não tem permissão para informar dados desta instituição.')
        
        return data

    def create(self, validated_data):
        validated_data['usuario_informacao'] = self.context['request'].user
        return super().create(validated_data)

class DadosAlunosSerializer(serializers.ModelSerializer):
    instituicao_nome = serializers.CharField(source='instituicao.nome', read_only=True)
    competencia_periodo = serializers.CharField(source='competencia.periodo', read_only=True)
    
    class Meta:
        model = DadosAlunos
        fields = '__all__'

# ========== SERIALIZERS PARA DASHBOARD ==========
class DashboardCustoAlunoSerializer(serializers.ModelSerializer):
    instituicao_nome = serializers.CharField(source='instituicao.nome', read_only=True)
    competencia_periodo = serializers.CharField(source='competencia.periodo', read_only=True)
    municipio_nome = serializers.CharField(source='instituicao.municipio.nome', read_only=True)
    uf_sigla = serializers.CharField(source='instituicao.municipio.uf.sigla', read_only=True)
    
    class Meta:
        model = DashboardCustoAluno
        fields = '__all__'

class SolicitacaoCadastroSerializer(serializers.ModelSerializer):
    instituicao_nome = serializers.CharField(source='instituicao.nome', read_only=True)
    
    class Meta:
        model = SolicitacaoCadastro
        fields = '__all__'
    
    def create(self, validated_data):
        return SolicitacaoCadastro.objects.create(**validated_data)

# ========== SERIALIZERS PARA RELATÓRIOS ==========
class RelatorioCustoSerializer(serializers.Serializer):
    instituicao_id = serializers.IntegerField(required=False)
    competencia_id = serializers.IntegerField(required=False)
    ano = serializers.IntegerField(required=False)
    
    total_gastos_operacionais = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_folha_pagamento = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_geral = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    quantidade_alunos = serializers.IntegerField(read_only=True)
    custo_por_aluno = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)