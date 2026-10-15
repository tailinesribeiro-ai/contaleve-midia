# Agente de postagem do Conta Leve: procedimento

Este arquivo é o manual do agente que roda sozinho, como tarefa agendada, às 6h50, 10h50 e 15h50 (horário da Bahia). A tarefa só diz "siga tools/AGENTE.md". Para mudar o comportamento do agente, edite este arquivo.

## Endereços fixos
- **Estúdio** (artifact com banco de dados): https://claude.ai/artifact/FGkKvcusaTjsQ7ewc85t4V. Ler e escrever com a ferramenta **ArtifactData**; ler o HTML com **Artifact** `action: "read"`.
- **Metricool**: brand/blogId `7446175`, Instagram `contaleve.wt`, fuso `America/Bahia`.
- **Mídias públicas**: este repositório (`tailinesribeiro-ai/contaleve-midia`, ramo `main`). URL pública de um arquivo: `https://raw.githubusercontent.com/tailinesribeiro-ai/contaleve-midia/main/<caminho>`.
- **Limite do Metricool grátis**: 20 posts por mês. Só Reels e carrosséis do Feed passam pelo Metricool. Stories e Status do WhatsApp são postados à mão por Wesley e Tai; o agente só deixa os arquivos prontos.

## Regras que nunca mudam
1. **Só agenda post com status exatamente "Pronto para postar"**, com `data` e `hora`. Esse status é a autorização de Wesley e Tai. Nada mais vai ao ar.
2. **Nunca altera o conteúdo** de um post (telas, legenda, título). Só muda `status`, `link`, `res`, `metricool`, `midias`, `publicadoEm`, `avisoAgente`.
3. Nunca apaga posts. Nunca publica nada fora do Instagram @contaleve.wt.
4. Toda escrita no banco usa `if_version` do documento lido. Se der conflito, reler e refazer só aquela escrita.
5. Se algo falhar, registrar o aviso no log (passo 6) e seguir com o resto. Na dúvida, não postar e avisar.

## Passo a passo de cada execução

### 1. Ler o estado
- `ArtifactData list` na coleção `posts` (limit 1000, com `out_dir` em uma pasta temporária) e na coleção `config`.
- Hora atual: usar a ferramenta de data e hora (fuso America/Bahia).

### 2. Sincronizar o Instagram com o estúdio
- Metricool `getAnalyticsDataByMetrics`, dos últimos 30 dias até agora:
  - Posts do feed: `IGPO02, IGPO06, IGPO07, IGPO03, IGPO14, IGPO28, IGPO13, IGPO08, IGPO15, IGPO27, IGPO29` (data, url, tipo, legenda, alcance, views, curtidas, comentários, salvamentos, compartilhamentos, seguidores ganhos).
  - Reels: `IGRE02, IGRE06, IGRE03, IGRE11, IGRE23, IGRE10, IGRE07, IGRE12, IGRE21, IGRE24` (data, url, legenda, alcance, views, curtidas, comentários, salvamentos, compartilhamentos, tempo médio em segundos).
  - Perfil por dia: `IGEV01, IGEV43, IGEV44, IGEV06, IGEV05, IGEV42` (seguidores, ganhos, perdidos, alcance, views, contas engajadas). O seguidor atual é o último valor não vazio de IGEV01.
- Para cada post publicado no Instagram, achar o post do estúdio, nesta ordem:
  1. `link` igual à url;
  2. `metricool.uuid`, quando `getScheduledPosts` mostrar aquele uuid com `publicUrl` igual à url;
  3. os primeiros 60 caracteres da legenda iguais (ignorar espaços e quebras de linha).
- Ao achar, gravar com `update`:
  - `status: "Publicado"`, `link`, `publicadoEm` (AAAA-MM-DDTHH:MM);
  - `res: {alcance, views, tempo, curt, coment, compart, salv, seg, medido: <hoje>, fonte: "metricool"}`, sempre só com os campos que vierem.
- Se um post do Instagram não existir no estúdio, criar com `set` um documento de id `ig_<código do link>`:
  - `nome` = 1ª linha da legenda (até 60 caracteres);
  - `canal` = "Instagram Reels" ou "Instagram Feed";
  - `status: "Publicado"`, `data`, `hora`, `legenda`, `link`, `res`, `origem: "instagram"`, `slides: []`, `ordem: 999`.
- Post do estúdio com status "Publicado", canal Feed ou Reels, data de até 14 dias atrás e sem link achado: aviso "<nome> está como Publicado mas não aparece no Instagram".
- Gravar `config/metricas` com `set`:
  - `seguidores`, `seguidoresEm`, `atualizado` (AAAA-MM-DDTHH:MM);
  - `dias: [{d, alcance, views, ganhos, perdidos, engajadas}]` dos últimos 30 dias;
  - `cota: {mes: AAAA-MM, usados, limite: 20}`;
  - `avisos: [...]` desta execução.
- **Comentários:** o Metricool só entrega o número de comentários, não o texto. Se um post tiver 3 ou mais comentários novos, avisar "<nome> tem N comentários: vale responder".

### 3. Contar a cota do mês
- `getScheduledPosts` do dia 1º do mês até o fim do mês (`extendedRange: false`). `usados` = quantidade de itens com rede instagram.
- Se `usados >= 20`, não agendar nada e avisar "Cota do Metricool do mês acabou".

### 4. Agendar o que foi autorizado
Candidatos: posts com `status == "Pronto para postar"`, `data` e `hora` preenchidos, e horário entre agora + 15 min e agora + 36 h.
- Horário que já passou: não postar. Avisar "<nome> estava Pronto para postar, mas o horário passou. Escolha um novo horário".
- Sem data ou sem hora: avisar e pular.

Para cada candidato, conforme o canal:

**Instagram Feed (carrossel ou foto)**
1. Ler o HTML do estúdio com Artifact `read` (url do estúdio). O resultado diz em que arquivo salvou a página.
2. Baixar as fotos usadas nas telas: para cada `foto` não vazia em `slides`, chamar Artifact `read` com `url` do estúdio e `path` = id do asset. Copiar cada arquivo para `blobs/<id>`.
3. Salvar o post (os campos do documento) em `post.json` e rodar:
   `python3 tools/render.py --studio <html> --post post.json --blobs blobs --out posts/<data>-<id>`
4. Conferir que saiu 1 JPG por tela e que `erros` está vazio. Abrir a 1ª imagem (ferramenta Read) e conferir se o texto apareceu (fontes carregadas). Se algo estiver errado, avisar e não agendar.
5. `git add`, commit "Post <id> (<data>)", `git push`. Conferir com curl que a URL pública da 1ª imagem responde 200.
6. Metricool `createScheduledPost`:
   - `date` = data e hora com -03:00;
   - `providers` instagram, `instagramData.type` "POST", `isAiGenerated` false;
   - `text` = legenda do estúdio sem nenhuma alteração; `media` = URLs públicas em ordem;
   - `autoPublish` true, `draft` false.
7. No estúdio, `update` do post:
   - `status: "Agendado"`;
   - `metricool: {id, uuid, hash}`, com o hash de `python3 tools/hash_post.py post.json`;
   - `midias` = lista de URLs.

**Instagram Reels**
- Precisa ter `pronto` (id do vídeo anexado). Se não tiver: avisar "<nome> é Reels sem vídeo pronto anexado" e pular.
- Baixar o vídeo com Artifact `read` (path = id) e salvar em `posts/<data>-<id>/video.mp4`. Commit, push e curl 200.
- `createScheduledPost` com `instagramData.type` "REEL", `showReelOnFeed` true, `isAiGenerated` true quando o roteiro ou o nome citar Gemini ou IA.
  - Se o post tiver `teste.variante` e o roteiro pedir "Reels de teste", usar "TRIAL_REEL".
- Atualizar o estúdio como no Feed.

**Instagram Stories, Status do WhatsApp e Live**
- Não passam pelo Metricool, para poupar a cota.
- Para Stories e Status: renderizar como no Feed, subir as imagens e gravar no post `midias` (URLs) e `avisoAgente: "Arquivos prontos para postar à mão"`. O status do post continua igual.
- Live: só lembrar no log, no dia, "Live hoje às <hora>".

### 5. Conferir o que já foi agendado
- Para posts com `status == "Agendado"`:
  - Se o hash atual for diferente de `metricool.hash`, o post foi editado depois de agendado. Renderizar de novo, subir e chamar `updateScheduledPost` com o conteúdo novo. Atualizar `metricool` com o novo id e o novo hash.
  - Se o Metricool mostrar `PUBLISHED`, marcar "Publicado" com o `link` (`publicUrl`).
  - Se mostrar erro, avisar com a mensagem do Metricool e voltar o status para "Pronto para postar".

### 6. Registrar o que fez
- `set` na coleção `agente`, documento de id = AAAA-MM-DDTHH-MM:
  - `{quando: "AAAA-MM-DDTHH:MM", resumo: "1 frase: o que sincronizou, o que agendou (nome e hora)", avisos: [..], agendados: [ids], publicados: [ids]}`.
- O Painel do estúdio mostra os 5 últimos registros. Escrever para Wesley e Tai, em português simples.

### 7. Aprendizados
- Se um post publicado há 3 dias ou mais tiver resultado bem acima ou bem abaixo da média dos últimos 30 dias, sugerir um aprendizado no log ("Sugestão de aprendizado: ..."). **Não gravar** em `config/aprendizados`: quem decide são Wesley e Tai, pelo botão do estúdio.
