# BrasilTech — loja de hardware

Projeto didático com Python, Flask, Jinja, CSS responsivo e SQLite. O banco é criado e preenchido automaticamente em `instance/brasiltech.db`. Os módulos antigos de MariaDB foram preservados como referência; o novo ponto de entrada usa `store.py`.

## Executar no Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install Flask==3.1.3
.\.venv\Scripts\python app.py
```

Acesse http://127.0.0.1:5000. Não é necessário instalar MariaDB para esta versão.

## Contas de demonstração

| Perfil | E-mail | Senha |
|---|---|---|
| Administrador | admin@brasiltech.com | Admin@123 |
| Cliente | ana@email.com | Cliente@123 |
| Cliente | pedro@email.com | Cliente@123 |

## Roteiro da aula

1. Explore a vitrine, pesquise Ryzen e filtre categorias.
2. Adicione produtos ao carrinho e aplique BRASIL10.
3. Entre como Ana, confirme a compra e veja o pedido.
4. Saia e entre como administrador. Confira a venda e os produtos vendidos.
5. Crie um cupom de 15% e publique um novo banner. Volte à vitrine para mostrar a campanha.
6. Mostre que o cliente não consegue abrir `/admin`.

O banco inclui oito produtos, dois clientes e uma venda inicial de exemplo. As compras são simuladas, sem gateway de pagamento ou cobrança. Os preços e especificações são dados ilustrativos. As representações dos produtos são ilustrações em CSS, não fotos comerciais.

## Organização e segurança

`app.py` inicia o servidor; `store.py` contém rotas, regras e consultas parametrizadas; `templates/` contém as telas Jinja; `static/css/store.css` contém a identidade visual. Valores monetários são armazenados em centavos. O fechamento da compra usa transação e verifica o estoque. Senhas são armazenadas com hash, formulários usam CSRF e o acesso administrativo é validado no servidor.

Para uma chave de sessão persistente, configure SECRET_KEY no ambiente. Sem ela, reiniciar o servidor encerra as sessões anteriores. As contas e senhas públicas são apenas para apresentação local; altere-as antes de disponibilizar o projeto na internet.

Testes: `python -m unittest test_store -v`. Usam banco temporário separado. O modo escuro é padrão e a identidade combina verde, amarelo e azul. A fonte externa é opcional; sem internet, Arial é utilizada.
