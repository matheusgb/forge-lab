# P06: Quando parar de chamar um provedor?

Este projeto usa dois mecanismos para proteger uma integração: um interrompe chamadas
durante uma falha contínua e o outro limita rajadas geradas pela própria aplicação.

## Como o programa funciona

Toda chamada passa primeiro pelo circuit breaker e depois pelo token bucket. O provider
fake só é chamado quando os dois permitem.

```text
chamada
   |
circuit breaker
   |
token bucket
   |
provider fake
```

Após três falhas, o circuito abre por cinco segundos. Depois desse intervalo, uma
chamada de teste verifica a recuperação. O bucket começa com três tokens, gasta um por
chamada e repõe um por segundo.

## Conceitos abordados

Circuit breaker, ou disjuntor, evita insistir em uma dependência indisponível. Ele usa
três estados:

- `closed`: as chamadas seguem normalmente;
- `open`: as chamadas são recusadas sem chegar ao provedor;
- `half-open`: uma chamada de teste decide se o provedor se recuperou.

Token bucket, ou balde de fichas, limita a taxa local. Cada chamada consome um token.
Quando o bucket fica vazio, a aplicação recusa novas chamadas até a reposição.

Os mecanismos resolvem problemas diferentes. O circuito reage à saúde do provedor. O
bucket controla o volume enviado pela aplicação.

## Para que isso serve em produção

Sem proteção, uma dependência lenta pode consumir conexões, threads e tempo até afetar
todo o sistema. Uma rajada também pode ultrapassar a cota de uma API saudável.

Exemplo: um provedor de frete fica indisponível. Depois das primeiras falhas, o circuito
recusa novas cotações localmente e preserva recursos da API. Quando o provedor volta,
uma única chamada testa a recuperação. Em outro momento, uma campanha gera centenas de
consultas ao mesmo tempo. O token bucket libera apenas a taxa combinada com o provedor.

## Como executar

```bash
make setup
make check
make experiment
```

O experimento usa um relógio manual e resultados definidos no `scenario.yaml`. Ele não
acessa a internet nem usa espera real.

## Resultado observado

| Condição | Resultado |
| --- | --- |
| terceira falha consecutiva | circuito aberto |
| chamada durante circuito aberto | recusada sem chegar ao provider |
| falha no `half-open` | circuito aberto por mais cinco segundos |
| sucesso no `half-open` | circuito fechado e contador zerado |
| cinco chamadas com três tokens | três permitidas e duas recusadas |
| um segundo de reposição | uma nova chamada permitida |

Dezoito testes, Ruff e Pyright passaram. A busca pelo segredo sintético encontrou zero
ocorrências nos logs e na evidência. O resultado completo está em
`evidence/result.txt`.

## Configuração e segredo

`ProviderConfig.from_env()` lê a credencial de uma variável de ambiente. O campo usa
`repr=False`, e os logs não recebem seu valor. Esse teste cobre os caminhos de log do
projeto, mas não substitui armazenamento seguro, controle de acesso ou rotação.

## Limite do projeto

O circuito e o bucket vivem em um único processo e não possuem sincronização entre
threads. Instâncias diferentes teriam contagens separadas. O provider é um fake, e o
projeto não implementa retry, limite distribuído ou gestão real de segredos.

## Resumo da ópera

O circuit breaker evita chamadas sem chance de sucesso. O token bucket contém o volume
enviado por uma instância. Em produção, os dois reduzem o impacto de falhas e rajadas,
mas o estado local não coordena várias instâncias.
