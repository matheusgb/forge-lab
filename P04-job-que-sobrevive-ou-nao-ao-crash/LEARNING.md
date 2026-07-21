# Registro de aprendizado

## Premissa

Uma espera com `time.sleep` representa uma biblioteca síncrona. Quatro requisições
usam o mesmo atraso local. Um processo Uvicorn filho representa a unidade que pode
encerrar durante uma `BackgroundTask`.

## Meta

Observar a diferença entre `def` e `async def` diante de código bloqueante, fechar os
recursos exatamente uma vez e demonstrar que uma tarefa aceita pode ser perdida após
um crash.

## Medido

- ambiente: Python 3.14.6, FastAPI 0.139.2, Uvicorn 0.51.0 e httpx2 2.7.0;
- Ruff e Pyright: nenhum erro encontrado;
- testes: 7 testes passaram;
- quatro requisições com espera bloqueante de 0,15 s levaram 0,161 s na rota
  `def` e 0,620 s na rota `async def` bloqueante, uma razão de 3,85 vezes;
- `graceful shutdown`: cliente e recurso fecharam exatamente uma vez;
- crash controlado: o job registrou um início e nenhuma conclusão;
- falha no startup: o recurso falhou e o cliente já adquirido foi fechado;
- falha no shutdown: o recurso falhou ao fechar e a limpeza do cliente ainda ocorreu.

## O que é `graceful shutdown`

`Graceful shutdown` é o encerramento controlado da aplicação. O processo recebe um
sinal para parar, mas não termina imediatamente. Primeiro, o servidor deixa de aceitar
novo trabalho, permite que as requisições em andamento terminem dentro do limite
configurado e executa a parte de shutdown do lifespan. Nesse momento, a aplicação pode
fechar conexões, liberar arquivos e concluir outras limpezas.

Neste laboratório, o processo Uvicorn recebe um sinal de término. O lifespan registra
`application_stopping`, fecha o recurso e fecha o cliente. A evidência mostra uma única
chamada de fechamento para cada componente.

O crash controlado segue outro caminho. O processo é interrompido sem oportunidade de
executar o shutdown. Por isso, a `BackgroundTask` registra `job_started`, mas não
registra `job_completed`. Os eventos de fechamento também não aparecem.

O `graceful shutdown` reduz a chance de interromper trabalho, mas não oferece garantia
ilimitada. Um servidor pode impor um tempo máximo e forçar o encerramento se alguma
operação demorar demais.

## Escolha e consequência

O `ExitStack` deixa a ordem de aquisição e limpeza explícita e continua fechando os
componentes restantes quando um deles falha. A rota `def` usa o thread pool oferecido
pelo FastAPI. Isso protege o event loop, mas não cria capacidade ilimitada.

## Próximo limite

O projeto não implementa uma fila durável. Para garantir recuperação, seria necessário
persistir o job antes da resposta e executá-lo em outro processo com retry e
idempotência.
