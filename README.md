# BrasilTech

Loja de hardware de demonstração para a disciplina de Programação Web. Usa Python, Flask e SQLite.

## Executar

```bash
pip install -r requirements.txt
python app.py
```

Abra http://127.0.0.1:5000.

Na primeira execução, o banco de exemplo em `demo/brasiltech.db` é copiado para `instance/brasiltech.db`. O arquivo em `instance/` guarda as alterações locais e não é enviado ao GitHub. Para recomeçar com os dados de exemplo, pare o servidor e remova `instance/brasiltech.db`.

## Contas de demonstração

| Perfil | E-mail | Senha |
| --- | --- | --- |
| Administrador | admin@brasiltech.com | Admin@123 |
| Cliente | ana@email.com | Cliente@123 |
| Cliente | pedro@email.com | Cliente@123 |

Os dados e pedidos são fictícios. Esta aplicação é um projeto acadêmico, não uma loja para vendas reais.

Veja [APRESENTACAO.md](APRESENTACAO.md) para um resumo das funcionalidades.
