# API de carrinho
1. Requer Python 3.11+: `python -m venv .venv` e ative o ambiente virtual.
2. Instale dependências: `pip install -r requirements.txt`.
3. Copie `.env.example` para `.env`; nenhuma variável é obrigatória nesta versão.
4. Inicie a API: `uvicorn main:app --reload`.
5. Calcule: `POST /cart/total` com `items` e opcionalmente `coupon`; valores de resposta são reais (`float`).
6. Rode testes: `pytest -q`.
7. `requirements.txt` registra dependências reproduzíveis; `.env` mantém configurações locais fora do Git e o `.gitignore` protege segredos.
8. Decisão: preços e totais são convertidos para centavos inteiros para evitar erros de ponto flutuante; cupons ficam em memória.
9. IA: Codex com gpt-luna6 apoiou a implementação; pedi API e cobertura de regras, revisei e corrigi cálculo e casos de validação.
