# Registro de aprendizado

## Premissa

Um provider fake representa a integração externa. Um relógio manual controla o circuito
e a reposição dos tokens. O cenário usa uma única execução sequencial e não acessa a
rede.

O segredo é um valor sintético carregado por configuração. Ele serve apenas para testar
se os logs expõem a credencial.

## Meta

Abrir o circuito após três falhas seguidas, recusar chamadas durante cinco segundos,
testar a recuperação com uma chamada no `half-open` e fechar o circuito após um sucesso.

Limitar uma rajada de cinco chamadas a três permissões. Repor uma permissão depois de um
segundo e manter o segredo fora dos logs e da evidência.

## Medido

- ambiente: Python 3.14.6;
- Ruff e Pyright: nenhum erro encontrado;
- testes: 18 testes passaram em 0,02 s;
- a terceira falha consecutiva mudou o circuito de `closed` para `open`;
- uma chamada imediata foi recusada e o provider permaneceu com três chamadas;
- em 5,0 s, a primeira sonda falhou e mudou o circuito de `half-open` para `open`;
- em 10,0 s, a segunda sonda funcionou e mudou o circuito para `closed`;
- a rajada de cinco chamadas permitiu três e recusou duas;
- depois de 1,0 s, um token foi reposto e uma nova chamada chegou ao provider;
- a busca pelo segredo controlado encontrou zero ocorrências nos logs e na evidência;
- nenhum teste ou experimento usou espera real.

## Escolha e consequência

O circuito envolve o token bucket. Essa ordem impede que uma chamada recusada durante o
estado `open` consuma um token. Em contrapartida, uma recusa por falta de tokens pode
cancelar uma sonda no `half-open`, que continuará esperando uma chamada real.

Somente `ProviderUnavailable` entra na contagem do circuito. Erro de autenticação e
limite local são devolvidos sem abrir o circuito. Essa escolha exige classificar os erros
na fronteira com o provedor.

O campo da credencial usa `repr=False`, e nenhum logger recebe o valor. Isso reduz um
caminho comum de vazamento, mas o segredo ainda existe na memória do processo.

## Próximo limite

O estado não é compartilhado entre processos e não usa sincronização entre threads. Um
próximo experimento poderia comparar estado local e distribuído sob concorrência. Gestão
real de segredos, rotação de credenciais e integração HTTP também não foram testadas.
