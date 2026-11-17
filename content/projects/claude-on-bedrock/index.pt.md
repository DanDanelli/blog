---
title: "Claude na AWS"
description: "Claude para uma empresa inteira através do Amazon Bedrock: Claude Desktop e Claude Code atrás de um Claude Apps Gateway privado, ferramentas atrás do AgentCore Gateway com uma política Cedar, e toda chamada de ferramenta feita como o usuário."
draft: false
weight: 10
status: "Deployed"
track: "Work"
series: ["Claude on AWS, the hard way"]
stack: ["Amazon Bedrock", "Claude Apps Gateway", "AgentCore Gateway", "AgentCore Identity", "Cedar", "Entra ID", "MCP", "Terraform"]
repo: ""
---

Uma plataforma corporativa que coloca o Claude à disposição de uma empresa inteira, com o modelo rodando no Amazon Bedrock na UE. As pessoas usam o Claude Desktop (Chat, Cowork e Code) e a CLI do Claude Code como usariam normalmente. Por trás delas, a plataforma decide quais modelos cada pessoa pode usar e quanto pode gastar, quais ferramentas pode chamar, e garante que toda chamada de ferramenta chegue ao Microsoft 365, Jira, Confluence ou SAP LeanIX **como a pessoa que pediu**.

## Em resumo

| | |
|---|---|
| **Usuários** | A empresa inteira, algumas centenas de pessoas |
| **Clientes** | Claude Desktop (Chat, Cowork, Code) e a CLI do Claude Code |
| **Modelo** | Claude no Amazon Bedrock, apenas com perfis de inferência da UE |
| **Ferramentas** | Microsoft 365 e SharePoint, Jira e Confluence, SAP LeanIX |
| **Identidade** | Microsoft Entra ID, para o modelo e para as ferramentas |
| **Governança** | Níveis de modelo e limites de gasto por pessoa no Claude Apps Gateway; uma política Cedar por ferramenta no AgentCore Gateway |
| **Ambientes** | Não produção e produção, em contas AWS separadas, tudo em Terraform |
| **Conteúdo de conversas armazenado na AWS** | Nenhum, por decisão |

## A ideia em uma frase

**O agente roda na máquina do usuário; a AWS hospeda só o que ele precisa alcançar.** Quando alguém pede ao Claude para encontrar um documento e resumi-lo, o loop que decide qual ferramenta chamar roda no app, no notebook da pessoa. A AWS hospeda o modelo, as ferramentas e a identidade que permite a cada ferramenta agir como o usuário. A maior parte da plataforma é a governança em torno dessas três coisas.

## Como uma requisição percorre o sistema

{{< diagram src="request-path.png" alt="Como uma requisição percorre o sistema: o caminho do modelo pelo Claude Apps Gateway até o Bedrock, e o caminho das ferramentas pelo OAuth shim e pelo AgentCore Gateway até Microsoft 365, Atlassian e SAP LeanIX" caption="O caminho do modelo (em cima) e o caminho das ferramentas (embaixo). Diagrama em inglês" >}}

Dois caminhos saem do notebook, e eles não compartilham nada além do provedor de identidade.

**Caminho B, o modelo** (passos 1 a 4):

1. O app faz login no gateway com um device code. O gateway devolve sua configuração: os modelos que essa pessoa pode usar, o conector de ferramentas gerenciado e as configurações do cliente.
2. O gateway autentica o usuário no Entra ID pelo seu próprio app registration. As App Roles do Entra decidem o nível da pessoa.
3. Toda requisição ao modelo vai para o gateway, em um endereço privado, pela rede corporativa.
4. O gateway confere o modelo contra o nível da pessoa e o gasto contra o limite dela, e então chama o Bedrock com SigV4, numa sessão com o nome do usuário. É essa sessão que permite atribuir a fatura, o export CUR 2.0, a cada pessoa. As métricas de uso dos clientes seguem o mesmo caminho: o gateway as repassa a um OpenTelemetry Collector ao lado dele, que remove a identidade e as grava no CloudWatch.

**Caminho A, as ferramentas** (passos 5 a 8):

5. O conector de ferramentas faz login no Entra ID separadamente (PKCE) e recebe um token para o plano de ferramentas.
6. As chamadas de ferramenta vão por MCP para um **OAuth shim**. Ele só existe porque o login de conectores do Claude espera recursos de OAuth que o Entra não oferece. Ele cuida do login e repassa o tráfego das ferramentas sem alterar nada.
7. O **AgentCore Gateway** valida o token Entra do usuário. Seu **motor de políticas Cedar** decide se aquela ferramenta pode rodar, e tudo que não tem política é negado. Uma Lambda interceptadora em toda chamada registra qual operação realmente rodou.
8. O **AgentCore Identity** obtém um token para *esta pessoa e este sistema*, e a chamada chega ao sistema como o usuário.

## Como a identidade de cada pessoa chega às ferramentas

{{< diagram src="identity-to-tools.png" alt="Como a identidade de cada usuário chega às ferramentas: login no Entra, AgentCore Gateway, políticas Cedar, AgentCore Identity e os sistemas de destino, com os três filtros em cada requisição" caption="Simplificado: o OAuth shim e o interceptador ficaram de fora, porque nenhum dos dois muda de quem é a identidade que a chamada carrega. Diagrama em inglês" >}}

Toda requisição de ferramenta passa por três filtros, e cada um pertence a um dono diferente:

| Filtro | Onde | Decide |
|---|---|---|
| **Entrada** | Entra ID, por pessoa | Se essa pessoa pode usar a plataforma |
| **Ferramentas** | Cedar, igual para todos | O que o agente pode fazer em cada sistema |
| **Dados** | O sistema de destino, por pessoa | O que essa pessoa pode ver e alterar |

A granularidade está no terceiro filtro, e isso é proposital. Duas pessoas que pedem o resumo do mesmo documento recebem respostas diferentes se só uma delas consegue abri-lo no SharePoint. **A plataforma não abre nada que a pessoa já não pudesse abrir.**

Como cada sistema obtém seu token:

| Sistema | Como o token é obtido | O que o agente pode fazer |
|---|---|---|
| Microsoft 365 | Troca on-behalf-of com o Entra, sem consentimento extra | Ler e escrever, incluindo links de compartilhamento |
| Atlassian | Consentimento único da pessoa, por um portal de consentimento | Ler e escrever; ações destrutivas bloqueadas |
| SAP LeanIX | Consentimento único da pessoa, por um portal de consentimento | Somente leitura |

O modelo tem limites, e eles estão declarados em vez de serem descobertos depois. Permissões amplas continuam amplas, e um agente torna mais fácil encontrar o que elas expõem. E um agente pode agir *dentro* das permissões de uma pessoa, mas *contra* a intenção dela: um documento que ele lê pode tentar induzir uma escrita. É para isso que serve a política por ferramenta.

## Os componentes, e por que cada um está lá

Cada componente precisou responder uma pergunta antes de ficar: *o que quebra se ele for removido?*

| Componente | O que faz | O que quebra sem ele |
|---|---|---|
| Claude Apps Gateway | Login, níveis de modelo, limites de gasto, configuração do cliente | Nenhum controle por pessoa sobre modelos ou gasto; de volta a um pacote por dispositivo |
| PostgreSQL | Sessões, rate limits, contadores de gasto | O gateway não consegue autenticar ninguém nem contar gasto |
| Load balancer interno e nome DNS | O endereço privado do gateway | Os clientes não alcançam o gateway |
| NAT gateway | Saída para o Entra ID, que não tem VPC endpoint | Ninguém consegue fazer login |
| OAuth shim | Preenche a lacuna entre o login de conectores do Claude e o Entra ID | O Claude Desktop não consegue fazer login nas ferramentas |
| AgentCore Gateway | O ponto de entrada único para todas as ferramentas | Nenhum lugar para aplicar políticas |
| Motor de políticas Cedar | Permite ou nega por ferramenta | Todas as ferramentas abertas para todos |
| AgentCore Identity | O cofre de tokens por pessoa e a troca de tokens | As ferramentas precisariam de identidade própria, e veriam tudo |
| Lambda interceptadora | Registra qual operação rodou por trás das ferramentas genéricas de um fornecedor | A trilha de auditoria diz `executeWrite` e nada mais |
| Sidecar do OpenTelemetry Collector | Grava as métricas dos clientes no CloudWatch, com uma allow-list de labels | Sem métricas de uso no mesmo dia; uma falha perde telemetria, nunca inferência |
| Export CUR 2.0 | A fatura, por pessoa, no dia seguinte | Nenhuma resposta com valor de fatura para *quem gastou quanto* |
| Política de proteção de dados da conta | Mascara JWTs, bearer tokens e segredos em todos os log groups | Credenciais legíveis nos logs |

O que **não** está lá importa tanto quanto. Não há agentes hospedados, índice vetorial de documentos da empresa, memória gerenciada nem prompts armazenados. Cada um desses foi recusado de propósito, com o que reverteria a decisão registrado por escrito.

## Governança

**Modelos e gasto.** Uma App Role do Entra coloca cada pessoa num nível, que decide os modelos que ela vê. Os limites de gasto são por pessoa e valem a partir da requisição seguinte à que ultrapassou o limite. Na prática, isso faz do limite um freio, não um teto rígido.

**Uso e custo.** Três fontes respondem três perguntas diferentes, e nenhuma delas guarda o que alguém escreveu:

| Fonte | O que contém | Por pessoa | Quando |
|---|---|---|---|
| As tabelas de gasto do gateway | Gasto por pessoa, a preço de tabela, como os limites o enxergam | Sim | No mesmo dia |
| Métricas do CloudWatch, pelo OpenTelemetry Collector | Tokens, custo, sessões e decisões de ferramentas, por modelo e tipo de token | Não, de propósito | Minutos |
| Export CUR 2.0 | A fatura, com o nome da sessão de cada pessoa em cada linha | Sim | No dia seguinte |

Os clientes enviam métricas OpenTelemetry pelo gateway para um collector que roda ao lado dele. O collector mantém uma **allow-list** de labels, então qualquer atributo de identidade que um cliente adicionar no futuro é descartado sem que ninguém precise saber o nome dele. Remover labels mudou a conta: pontos delta que só diferiam num label removido eram descartados como duplicados, e os tokens ficavam subcontados. Agora o collector alinha os horários de início desses pontos para que eles se somem, e uma métrica conta qualquer ponto que ainda seja descartado.

O export de faturamento bateu exatamente com as contagens de tokens do próprio Bedrock, em todos os modelos e tipos de token. A telemetria não: o Claude Desktop dá nome a cada conversa com uma pequena chamada ao modelo que nunca chega às métricas. Por isso, o CloudWatch serve para tendências, e a fatura serve para dinheiro. A atribuição dessas chamadas por pessoa no mesmo dia é uma lacuna que aceitamos, porque a única coisa que a fecha é armazenar todos os prompts.

**Ferramentas.** O Cedar decide quais ferramentas existem para quem, e uma ferramenta sem permissão fica escondida, não apenas recusada. Onde nós controlamos a linha entre leitura e escrita, há uma permissão por ferramenta. Onde um fornecedor expõe centenas de operações por trás de poucas ferramentas genéricas, a política só consegue governar essas ferramentas, e uma linha de auditoria registra a operação.

**Observabilidade.** Sem log de prompts, por decisão: a plataforma transporta o conteúdo das conversas e não o armazena. Os valores dos parâmetros das ferramentas são mascarados, e os nomes, mantidos. Uma política de proteção de dados na conta inteira mascara qualquer coisa com formato de credencial em todos os log groups, e um alarme dispara se alguma voltar a aparecer num log. O mascaramento esconde valores de quem lê; ele não os apaga, e a plataforma diz exatamente isso quando perguntada.

## A rede

O gateway não tem endereço público. A VPC de cada ambiente está conectada ao Transit Gateway da empresa, então os clientes chegam até ele por Direct Connect e pela rede corporativa, através de um nome DNS interno. Como a rede corporativa usa uma única tabela de rotas compartilhada, a separação entre ambientes fica por nossa conta, com network ACLs. Na saída, um NAT gateway leva o tráfego de login até o Entra ID, e todo o resto passa por VPC endpoints.

## O cliente

Um dispositivo gerenciado precisa de **uma configuração**: a URL de bootstrap do gateway. Os modelos, o conector de ferramentas e as configurações do cliente chegam no login e mudam sem tocar no dispositivo. Quem usa dispositivos não gerenciados importa o mesmo arquivo de uma linha. O que o gateway aplica não depende do caminho que o usuário seguiu, porque os controles que importam estão no servidor.

## Princípios de design

- **Decida o que não construir,** e registre cada "não" com o que o reverteria.
- **Toda ferramenta age como o usuário.** Nenhuma identidade de aplicação contra sistemas que guardam dados de usuários.
- **Nenhum container que seja só um proxy.** Nossos próprios servidores MCP foram aposentados; as ferramentas agora são um schema OpenAPI e os servidores dos próprios fornecedores.
- **Verifique antes cada destino de dados.** Antes de qualquer coisa receber dados, escreva o que vai parar nela. O mascaramento reconhece o formato de um segredo, nunca o lugar onde ele está.
- **Aplique no servidor, configure no cliente.**
- **Guarde as decisões revertidas por completo.** O raciocínio que produziu uma decisão errada é o raciocínio que alguém vai repetir.

## A série

*Claude on AWS, the hard way* acompanha a plataforma uma decisão de cada vez, da primeira tentativa até a versão que foi para produção, incluindo as tentativas que foram revertidas. É mais sobre decisões e percalços do que sobre código. Por enquanto, as notas da série estão em inglês.
