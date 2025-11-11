from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction, models
from .models import LancamentoGasto, FolhaPagamento, DadosAlunos, DashboardCustoAluno

@receiver([post_save, post_delete], sender=LancamentoGasto)
@receiver([post_save, post_delete], sender=FolhaPagamento)
@receiver([post_save, post_delete], sender=DadosAlunos)
def atualizar_dashboard(sender, instance, **kwargs):
    """
    Atualiza automaticamente o dashboard quando há mudanças nos dados
    """
    with transaction.atomic():
        instituicao = instance.instituicao
        competencia = instance.competencia
        
        # Verificar se existem dados completos para calcular
        try:
            dados_alunos = DadosAlunos.objects.get(
                instituicao=instituicao,
                competencia=competencia
            )
            quantidade_alunos = dados_alunos.quantidade_alunos
        except DadosAlunos.DoesNotExist:
            # Sem dados de alunos, não é possível calcular
            return
        
        # Calcular totais
        total_gastos_operacionais = LancamentoGasto.objects.filter(
            instituicao=instituicao,
            competencia=competencia
        ).aggregate(total=models.Sum('valor_total'))['total'] or 0
        
        total_folha_pagamento = FolhaPagamento.objects.filter(
            instituicao=instituicao,
            competencia=competencia
        ).aggregate(total=models.Sum('valor_total'))['total'] or 0
        
        total_geral = total_gastos_operacionais + total_folha_pagamento
        custo_por_aluno = total_geral / quantidade_alunos if quantidade_alunos > 0 else 0
        
        # Atualizar ou criar dashboard
        DashboardCustoAluno.objects.update_or_create(
            instituicao=instituicao,
            competencia=competencia,
            defaults={
                'total_gastos_operacionais': total_gastos_operacionais,
                'total_folha_pagamento': total_folha_pagamento,
                'total_geral': total_geral,
                'quantidade_alunos': quantidade_alunos,
                'custo_por_aluno': custo_por_aluno
            }
        )