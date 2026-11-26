# Planejamento da rede de atenção à saúde de Itaúna

UFMG — Pesquisa Operacional para Saúde.

Repositório: https://github.com/luana-soares/PO-Saude

## Requisitos e instalação

Python 3.10 ou superior e GLPK, com `glpsol` no PATH. A compilação do artigo requer XeLaTeX e `latexmk`, disponíveis nas distribuições TeX Live e MiKTeX. Os comandos abaixo são executados na raiz do projeto, exceto a compilação do artigo.

```powershell
python -m pip install -r requirements.txt
glpsol --version
python executar.py --verificar
```

O `pip` instala as bibliotecas Python; o GLPK e a distribuição LaTeX são instalações separadas.

## Execução dos modelos

A primeira etapa define as UBS, equipes, ACS e alocações populacionais. O complemento móvel atende a população sem cobertura geográfica e vincula os encaminhamentos à UBS-base. A etapa hierárquica mantém a rede primária fixa e resolve os seis cenários de encaminhamento.

```powershell
python executar.py --time-limit 600 --limite-hierarquia 120 --quiet --saida resultados/atual/plano
python executar.py --auditar --saida resultados/atual/plano
```

`--time-limit` é o limite em segundos por resolução da APS; `--limite-hierarquia`, por resolução especializada. Os resultados principais usam nível único por estabelecimento. Múltiplos níveis constituem a análise complementar.

Os custos e as análises usados nas figuras são atualizados pelos comandos seguintes:

```powershell
python executar.py --custo-equipes --saida resultados/atual/financeiro
python executar.py --investimento --plano resultados/atual/plano --saida resultados/atual/investimento
python executar.py --orcamento --plano resultados/atual/plano --saida resultados/atual/orcamento
python codigos/analises/rodar_sensibilidade.py --time-limit 600 --processos 3
python codigos/analises/cenario_leitos_otimista.py
python codigos/exportar_aps_mathprog.py
```

A sensibilidade inclui cobertura, raios urbano/rural, mínimo rural, crescimento e folga de custo. O cenário hospitalar favorável é calculado separadamente. O último comando atualiza os `.dat` da APS conforme o plano salvo; os `.dat` hierárquicos são gerados na execução do modelo.

## Gráficos e artigo

```powershell
python executar.py --graficos
```

O comando usa os resultados consolidados em `resultados/atual/`, substitui os gráficos e mapas em `imagens/`, atualiza o mapa interativo e os oito PDFs de figuras em `documentacao/artigo/figuras/`. Também atualiza `ABRIR_RESULTADOS.html`. Para reproduzir apenas as figuras dos resultados entregues, basta executar esse comando, sem reotimizar os modelos.

As cores são definidas em `codigos/paleta.py`: cinza para UBS existentes, roxo para novas urbanas, laranja para novas rurais e verde para equipes móveis. Comparações entre população urbana e rural usam roxo e laranja; outras variáveis têm legendas próprias.

Compilação do artigo:

```powershell
cd documentacao/artigo
latexmk -xelatex -interaction=nonstopmode planejamento_rede_saude_itauna.tex
Move-Item -LiteralPath planejamento_rede_saude_itauna.pdf -Destination ../../planejamento_rede_saude_itauna.pdf -Force
cd ../..
```

O PDF final, `planejamento_rede_saude_itauna.pdf`, fica na raiz do projeto. O fonte principal é `documentacao/artigo/planejamento_rede_saude_itauna.tex`, acompanhado de `detalhamento_metodologico.tex`, `resultados_artigo.tex`, `apendice_fontes.tex` e `figuras/`. As tabelas numéricas do texto LaTeX são estáticas e precisam ser revisadas se uma nova otimização alterar os resultados.

## Formulações MathProg

```powershell
glpsol -m modelos/aps.mod -d modelos/dados/aps_fase1.dat
glpsol -m modelos/aps.mod -d modelos/dados/aps_fase2.dat
glpsol -m modelos/aps.mod -d modelos/dados/aps_fase3.dat
glpsol -m modelos/rede_completa.mod -d modelos/dados/hierarquico_unico_via_50_fase1.dat
glpsol -m modelos/rede_completa.mod -d modelos/dados/hierarquico_unico_via_50_fase3.dat
```

Na APS, as fases maximizam cobertura, minimizam construção mais operação em cinco anos e minimizam deslocamento. A fase 3 admite folga de 2% somente no custo operacional. Os `.dat` entregues contêm as referências da execução salva. Para resolver as três fases MathProg e atualizar essas referências em sequência:

```powershell
python codigos/exportar_aps_mathprog.py --resolver --time-limit 600
```

O modelo hierárquico utiliza as fases 1 e 3: minimiza a falta de atendimento e, em seguida, a distância, mantendo a falta mínima. Os sufixos `via_25`, `via_50` e `via_75` representam a parcela da demanda terciária encaminhada pela secundária.

## Arquivos

| Caminho | Conteúdo |
|---|---|
| `executar.py` | Entrada principal |
| `modelos/` | Modelo Python da APS e formulações `.mod` |
| `modelos/dados/` | Entradas `.dat` |
| `codigos/` | Preparação, planejamento, encaminhamentos, indicadores e auditoria |
| `codigos/custos/` | Pessoal, construção e orçamento |
| `codigos/graficos/` | Mapas, gráficos e organização dos resultados |
| `codigos/analises/` | Sensibilidade e cenário hospitalar |
| `codigos/coleta/` | Consulta das instalações físicas no CNES |
| `dados/fontes/` | Arquivos Excel de entrada, configurações e fontes públicas |
| `dados/preparados/` | Tabelas intermediárias produzidas pelo código |
| `resultados/atual/` | Resultados numéricos e registros do solver |
| `imagens/` | Figuras e mapas para consulta |
| `planejamento_rede_saude_itauna.pdf` | PDF final do artigo |
| `documentacao/artigo/` | Fontes LaTeX e figuras do artigo |

As entradas incluem população territorial do IBGE, cadastro CNES, produção SIA/SIH e orçamento público. Fontes e critérios de estimação estão no artigo. A demanda especializada é estimada pela utilização registrada, projetada e distribuída proporcionalmente à população. Os custos de pessoal são estimativas por horas cadastradas e remunerações de referência. Funcionamento, construção e deslocamento são apresentados separadamente.

## Conferência dos resultados

```powershell
python executar.py --auditar --saida resultados/atual/plano
```

## Dados de entrada

As tabelas de entrada estão em arquivos `.xlsx` separados, na pasta `dados/fontes/`. Cada arquivo contém uma aba `Dados`. Os nomes correspondem aos conjuntos utilizados no modelo, como `pontos_demanda_itauna.xlsx`, `unidades_existentes_itauna.xlsx`, `ubs_recursos_cnes_202607.xlsx` e `custos_construcao_ubs_2025.xlsx`.

A leitura é feita por `codigos/tabelas.py`, com pandas e openpyxl. Os JSON guardam configurações e respostas originais de consultas públicas. As tabelas intermediárias e de resultados continuam em CSV; os modelos GLPK recebem os `.dat` gerados pelo Python. Não é necessário converter manualmente os Excel antes da execução.
