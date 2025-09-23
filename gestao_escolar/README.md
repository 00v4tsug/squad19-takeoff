# Gestão Escolar — Autenticação com Usuário Personalizado

Projeto Django com CustomUser (CPF, telefone, role) e painéis por perfil (Admin, Professor, Aluno).

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Acesse:
- /register/ — cadastro
- /login/ — login
- /painel/ — encaminha para o painel conforme o papel
- /admin/ — Django Admin
