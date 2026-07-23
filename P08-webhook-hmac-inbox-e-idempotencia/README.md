# P08: Caixa de entrada de webhook assinado

Este projeto recebe eventos enviados por outro sistema, verifica a origem da mensagem e
impede que a mesma entrega produza o efeito de negócio mais de uma vez.

## Como o programa funciona

O endpoint `POST /webhooks/payments` lê os bytes exatos da requisição. Ele valida o
timestamp e a assinatura HMAC antes de interpretar o JSON. Depois, salva o evento na
inbox e responde ao remetente. Um worker separado executa o efeito.

```text
provider
   |
   | timestamp + assinatura + corpo bruto
   v
validar HMAC e janela de tempo
   |
   v
salvar event_id único na inbox
   |
   +------> responder 202
   |
   v
worker aplica o efeito e marca processed
```

A inbox é uma caixa de entrada de eventos recebidos. Cada registro passa por um destes
estados:

- `received`: persistido e aguardando processamento;
- `processed`: efeito concluído;
- `failed`: evento mantido com o motivo da falha.

## Solução usada no projeto

O recebimento segue esta ordem:

1. O cliente envia `X-Webhook-Timestamp` e `X-Webhook-Signature`.
2. A assinatura cobre `timestamp + "." + corpo bruto` com HMAC-SHA256.
3. O servidor aceita timestamps dentro de uma janela de cinco minutos.
4. `hmac.compare_digest` compara as assinaturas sem usar uma comparação ingênua.
5. Pydantic transforma o JSON autenticado em um evento que a inbox salva com
   `event_id` único.
6. A API responde antes de executar o efeito demorado.
7. O worker busca o registro `received`, aplica o efeito uma vez e marca `processed`.

Pydantic só recebe o corpo depois da validação HMAC. Essa ordem mantém visível o ponto
central do projeto: a assinatura pertence aos bytes recebidos, não a um JSON
reinterpretado pela aplicação.

Três entregas idênticas criam um único registro. A primeira recebe `202 Accepted`. As
seguintes recebem `200` com `delivery: duplicate`. Se o mesmo `event_id` chegar com outro
corpo, a API retorna `409 Conflict` para não esconder uma inconsistência.

## Conceitos abordados

HMAC é um código de autenticação calculado com uma função de hash e um segredo
compartilhado. Ele permite detectar alteração do corpo e confirmar que o remetente
conhece o segredo. Ele não criptografa a mensagem.

A janela de timestamp reduz replay, que é o reenvio posterior de uma requisição válida.
Ela não substitui a unicidade do `event_id`: uma duplicata ainda pode chegar dentro dos
cinco minutos.

Idempotência significa que repetir a mesma operação mantém um único efeito lógico. A
inbox deduplica a entrega. O effect store também registra os IDs aplicados para que uma
recuperação depois do efeito não o execute novamente.

## Para que isso serve em produção

Providers reenviam webhooks quando não recebem resposta, quando ocorre timeout ou quando
o mecanismo de entrega trabalha no modelo at-least-once. Nesse modelo, a entrega pode
acontecer mais de uma vez.

Exemplo: um sistema de pagamento envia `payment.authorized`. A API salva o evento e cai
antes de o worker processá-lo. Depois da recuperação, o registro continua pendente e o
worker aplica o efeito. Se o provider também reenviar o evento, o `event_id` único impede
uma segunda autorização interna.

Em um sistema real, a inbox ficaria em um banco com uma constraint `UNIQUE` para
`event_id`. A resposta HTTP seria enviada somente depois do commit. O worker poderia
usar lock, lease ou uma fila para distribuir o processamento entre instâncias.

## Política para evento fora de ordem

O cenário usa dois tipos sintéticos:

```text
payment.authorized -> payment.captured
```

Se `payment.captured` chegar antes da autorização do mesmo pedido, a entrega é salva e o
worker marca o registro como `failed`. O motivo permanece visível. Este projeto não faz
replay automático quando a autorização chega depois. Essa decisão evita aplicar um
evento sem o pré-requisito e deixa a recuperação explícita.

## Como executar

```bash
uv sync --locked
uv run ruff check .
uv run pyright
uv run pytest
uv run python scripts/run_experiment.py
```

Para iniciar a API local:

```bash
P08_WEBHOOK_SECRET=local-demo-secret uv run uvicorn webhook_inbox.api:app --reload
```

A documentação interativa fica em `http://127.0.0.1:8000/docs`.

## Falhas reproduzidas

O experimento executa estes casos:

- corpo alterado com a assinatura original;
- timestamp mais antigo que a janela aceita;
- o mesmo evento entregue três vezes;
- crash depois da persistência e antes do efeito;
- captura recebida antes da autorização.

O resultado fica em `evidence/result.txt`.

## Resultado observado

**Medido:** três entregas criaram um registro e um efeito. O crash controlado deixou o
evento como `received` e sem efeito. A execução seguinte concluiu o mesmo evento. O
corpo alterado falhou na assinatura, o timestamp antigo foi rejeitado e o evento fora
de ordem terminou como `failed` com um motivo.

## Limite do projeto

O protocolo é sintético e não representa a especificação de um provider real. A inbox
e o effect store vivem em memória. Por isso, o experimento simula a interrupção do
worker, mas não prova sobrevivência a um processo ou máquina reiniciados. Banco durável,
concorrência entre workers, rotação de segredo e proteção após comprometimento do
segredo ficam fora do escopo.

## Resumo da ópera

Valide a assinatura sobre o corpo bruto, limite a idade da requisição e salve um
`event_id` único antes de responder. Execute o efeito fora da requisição e mantenha o
estado da inbox visível. Em produção, a mesma estrutura precisa de armazenamento durável
e unicidade garantida pelo banco.
