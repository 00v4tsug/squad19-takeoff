from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from app_principal.models import *

class Command(BaseCommand):
    help = 'Carrega dados iniciais para o sistema'
    
    def handle(self, *args, **options):
        self.stdout.write('Iniciando carga de dados iniciais...')
        
        # Criar UF e Municípios
        uf_sp, created = UnidadeFederativa.objects.get_or_create(
            sigla='SP',
            defaults={'nome': 'São Paulo'}
        )
        uf_rj, created = UnidadeFederativa.objects.get_or_create(
            sigla='RJ', 
            defaults={'nome': 'Rio de Janeiro'}
        )
        
        municipio_sp, created = Municipio.objects.get_or_create(
            nome='São Paulo',
            defaults={'uf': uf_sp}
        )
        municipio_rj, created = Municipio.objects.get_or_create(
            nome='Rio de Janeiro',
            defaults={'uf': uf_rj}
        )
        
        # Criar usuário admin
        CustomUser = get_user_model()
        if not CustomUser.objects.filter(username='admin').exists():
            admin_user = CustomUser.objects.create_superuser(
                username='admin',
                email='admin@sistema.com',
                password='admin123',
                first_name='Administrador',
                last_name='Sistema',
                cargo='ADMIN'
            )
            self.stdout.write(
                self.style.SUCCESS('✅ Superusuário criado: admin / admin123')
            )
        
        # Criar categorias de gasto
        categorias = [
            ('01', 'Pessoal', 'Despesas com pessoal'),
            ('02', 'Material', 'Material de consumo e expediente'),
            ('03', 'Serviços', 'Serviços terceirizados'),
            ('04', 'Manutenção', 'Manutenção e conservação'),
            ('05', 'Outros', 'Outras despesas'),
        ]
        
        for codigo, nome, descricao in categorias:
            CategoriaGasto.objects.get_or_create(
                codigo=codigo,
                defaults={'nome': nome, 'descricao': descricao}
            )
        
        # Criar itens de gasto
        itens_gasto = [
            ('Material Escolar', 'Material didático e escolar', '02'),
            ('Limpeza', 'Material de limpeza', '02'),
            ('Água', 'Conta de água', '03'),
            ('Luz', 'Conta de energia elétrica', '03'),
            ('Internet', 'Serviço de internet', '03'),
            ('Manutenção Predial', 'Manutenção do prédio', '04'),
            ('Transporte', 'Transporte escolar', '03'),
        ]
        
        for nome, descricao, codigo_categoria in itens_gasto:
            categoria = CategoriaGasto.objects.get(codigo=codigo_categoria)
            ItemGasto.objects.get_or_create(
                nome=nome,
                defaults={'descricao': descricao, 'categoria': categoria}
            )
        
        # Criar competência atual
        from datetime import datetime
        hoje = datetime.now()
        competencia, created = Competencia.objects.get_or_create(
            ano=hoje.year,
            mes=hoje.month,
            defaults={'aberta': True}
        )
        
        # Criar combo de gastos padrão
        combo, created = ComboGasto.objects.get_or_create(
            nome='Gastos Mensais Padrão',
            competencia=competencia,
            defaults={'descricao': 'Combo padrão para gastos mensais', 'ativo': True}
        )
        
        # Adicionar itens ao combo
        if created:
            itens_combo = [
                ('Material Escolar', 100, 50.00),
                ('Limpeza', 50, 25.00),
                ('Água', 1, 300.00),
                ('Luz', 1, 500.00),
                ('Internet', 1, 150.00),
            ]
            
            for nome_item, quantidade, valor in itens_combo:
                item_gasto = ItemGasto.objects.get(nome=nome_item)
                ItemCombo.objects.create(
                    combo=combo,
                    item_gasto=item_gasto,
                    valor_padrao=valor
                )
        
        self.stdout.write(
            self.style.SUCCESS('✅ Dados iniciais carregados com sucesso!')
        )
        self.stdout.write('')
        self.stdout.write('📋 Dados criados:')
        self.stdout.write('  • 2 UFs (SP, RJ)')
        self.stdout.write('  • 2 Municípios (São Paulo, Rio de Janeiro)')
        self.stdout.write('  • 1 Usuário Admin (admin/admin123)')
        self.stdout.write('  • 5 Categorias de gasto')
        self.stdout.write('  • 7 Itens de gasto')
        self.stdout.write('  • 1 Competência atual')
        self.stdout.write('  • 1 Combo de gastos padrão')