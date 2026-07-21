# Matriz de decisão

| Resultado do provedor | Leitura segura | Criação não idempotente |
| --- | --- | --- |
| `2xx` | devolver sucesso | devolver sucesso |
| `400` | parar, erro definitivo | parar, erro definitivo |
| `429` | repetir dentro do limite | parar, operação insegura |
| `5xx` | repetir dentro do limite | parar, operação insegura |
| timeout | repetir dentro do limite | parar, operação insegura |
| falha transitória na última tentativa | parar, limite esgotado | não chega a uma nova tentativa |

A leitura usa `GET` e pode ser repetida sem criar um novo efeito. A criação usa `POST`
e não recebe uma chave de idempotência neste laboratório. Por isso, um timeout pode
esconder uma criação concluída no provedor e o cliente não repete a chamada.
