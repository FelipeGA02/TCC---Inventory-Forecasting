---
name: "ata-reuniao"
description: "Gerar a ata (DOCX) de uma reunião com a Floricultura Verde Perto a partir da transcrição, no modelo exato do 'Formulário de Registro de Reuniões com Entidade' (atas 01–04 em Relatórios). Use sempre que o usuário passar uma transcrição de reunião com o cliente ou pedir a ata / registro de reunião."
argument-hint: "Caminho da transcrição (ou cole o texto) e observações (ex.: 'Carol também participou')"
user-invocable: true
disable-model-invocation: false
---

# Ata de reunião com a entidade

A ata é sempre o mesmo formulário de 10 seções, com logo, estilos, numeração, tabelas e
paginação das atas 01–04. Esta skill **não desenha nada**: escreve o conteúdo num JSON e o
`scripts/gerar_ata.py` monta o DOCX sobre `modelo/modelo_ata.docx`. O trabalho é ler a
transcrição e escrever, de forma sucinta, o que vai em cada campo.

## Entrada do usuário

```text
$ARGUMENTS
```

## Antes de começar, leia

`referencia/estrutura.md`: o que vai em cada seção, regras de escrita, participantes conhecidos e
os erros típicos da transcrição automática. Exemplo completo de saída: `exemplos/ata_05.json`.

## Fluxo

Pasta das atas: `C:\Users\felip\OneDrive\Documentos\Estudos\TCC\Relatórios`. Rodar os scripts com
`PYTHONIOENCODING=utf-8 python` (só biblioteca padrão). Arquivos de trabalho no scratchpad.

1. **Base**: `python scripts/ler_ata.py --ultima` imprime o caminho e o JSON da última ata. Daí
   saem o número (+1), projeto, entidade, validação, a tabela de requisitos (cumulativa) e as
   pendências que ainda podem estar abertas.
2. **Transcrição**: ler inteira antes de escrever. Separar por assunto: o que foi apresentado, o
   que o cliente pediu, o que foi decidido, o que ficou para depois e para quem.
3. **JSON**: copiar a base e reescrever cada campo seguindo `referencia/estrutura.md`. Formato:

   ```json
   {"projeto": "", "entidade": "", "numero": "05", "data": "20/10/2026",
    "inicio": "10:56", "termino": "11:28", "local": "online", "plataforma": "Google Meet",
    "participantes": [{"nome": "", "papel": ""}],
    "objetivo": "",
    "pauta": {"marcados": ["Apresentação de protótipo"], "outros": ""},
    "decisoes": ["texto", {"texto": "texto com subitens:", "subitens": ["a", "b"]}],
    "requisitos": [{"codigo": "REQ-01", "descricao": "", "prioridade": null}],
    "pendencias": [{"acao": "", "prazo": ""}],
    "impactos": {"marcados": ["Alteração de escopo"], "descricao": [""], "pontos_de_atencao": []},
    "proxima_reuniao": {"data": "", "objetivo": ""},
    "validacao": {"representante_cliente": "", "responsaveis": ["", ""]}}
   ```

   `pauta.marcados` usa os nomes exatos dos 5 itens fixos; `impactos.marcados`, os 4 nomes fixos.
   Nos textos, `**negrito**` e `\n` funcionam; em `impactos.descricao`, uma linha começando com
   `- ` vira bullet.
4. **Gerar**: `python scripts/gerar_ata.py <ata.json> "<pasta das atas>\Documento - Registro de
   Reuniao com Entidade NN.docx"`. Se o arquivo já existir, perguntar antes de sobrescrever.
5. **Conferir**: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/exportar_pdf.ps1 -In
   <ata.docx> -OutPdf <scratchpad>\ata.pdf` (caminhos Windows absolutos), depois
   `C:/Users/Felipe_2clix/.claude/tcc-env/Scripts/python.exe scripts/renderizar_pdf.py
   <scratchpad>\ata.pdf <scratchpad>\paginas` e ler `folha.png` com a ferramenta Read (o Read não
   abre PDF nesta máquina: falta o poppler). Verificar: pág. 1 termina na seção 3; seções 4, 6 e 9 abrem página; amarelo só
   nos itens de pauta tratados; nenhuma tabela com linha solitária na página seguinte (se houver,
   enxugar o texto); nenhum campo vazio que deveria estar preenchido.
6. **Responder** com o caminho do DOCX e, em poucas linhas: suposições feitas (participante fora
   da lista do transcritor, plataforma, horário de término), pendências da ata anterior que saíram
   e por quê, e qualquer decisão da reunião que contrarie o que está documentado no repositório
   (CLAUDE.md, ADRs), para o usuário decidir se atualiza a documentação.

## Não fazer

- Mudar a estrutura (seções, ordem, tabelas, textos fixos) ou editar o `modelo_ata.docx` à mão.
  Se o formulário mudar, gerar outro modelo: `python scripts/gerar_ata.py
  exemplos/modelo_em_branco.json modelo/modelo_ata.docx --modelo <nova ata>.docx`.
- Transcrever falas, citar quem disse o quê ou registrar conversa fora do assunto.
- Inventar dado que a transcrição não sustenta (data da próxima reunião, prioridade, nomes).
