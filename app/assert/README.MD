# Script de Teste de Performance das Rotas de Busca

Este script testa a performance das diferentes rotas de busca do sistema TangentCFT usando a base de dados de teste.

## Funcionalidades

O script testa 4 tipos diferentes de query:

1. **text_with_formulas_replaced** → endpoint `/search-pure-text`
2. **text_lightly_modified** → endpoint `/search-text-with-treated-formulas`
3. **text_semantically_modified** → endpoint `/search-text-vector`
4. **text_natural_language** → endpoint `/search-with-text-without-formula-combined-with-slt-formula-vector`

Para cada tipo de query, o script:

- Executa a busca usando a query correspondente
- Verifica se o post correto (post_id esperado) está nos top-K resultados
- Mede o tempo de resposta
- Calcula estatísticas de performance

## Como usar

### Pré-requisitos

1. Certifique-se de que o servidor da API está rodando:

```bash
cd app
python main.py
```

2. Instale as dependências necessárias:

```bash
pip install requests
```

### Execução básica

```bash
python test_search_performance.py
```

### Opções de linha de comando

```bash
python test_search_performance.py --help
```

**Parâmetros disponíveis:**

- `--data`: Caminho para o arquivo JSON com os dados de teste (padrão: `app/assert/questoes_formulas_selecionadas.json`)
- `--base-url`: URL base da API (padrão: `http://localhost:8000`)
- `--top-k`: Número de resultados top-k para avaliar (padrão: 10)
- `--output`: Arquivo para salvar os resultados detalhados (padrão: `test_results.json`)

### Exemplos de uso

```bash
# Teste básico
python test_search_performance.py

# Teste com top-5 resultados
python test_search_performance.py --top-k 5

# Teste com API em outra porta
python test_search_performance.py --base-url http://localhost:8080

# Teste com arquivo de dados personalizado
python test_search_performance.py --data meus_dados_teste.json

# Salvar resultados em arquivo específico
python test_search_performance.py --output meus_resultados.json
```

## Interpretação dos Resultados

### Métricas calculadas

- **Taxa de Sucesso**: Percentual de requisições que foram executadas com sucesso (sem erros HTTP)
- **Taxa de Acerto**: Percentual de casos onde o post correto foi encontrado nos top-K resultados
- **Posição Média**: Posição média onde o post correto foi encontrado (quando encontrado)
- **Tempo Médio**: Tempo médio de resposta das requisições

### Exemplo de saída

```
=== Testando text_with_formulas_replaced usando endpoint /search-pure-text ===
  Caso 1: Testando post_id 10347
    ✓ Encontrado na posição 1
  Caso 2: Testando post_id 11194
    ✗ Não encontrado no top-10
  Resumo: 12/12 sucessos (100.0%)
  Taxa de acerto no top-10: 8/12 (66.7%)
  Tempo médio de resposta: 0.245s

================================================================================
RESUMO FINAL DOS TESTES
================================================================================
Total de casos de teste: 12
Top-K avaliado: 10
Tipos de query testados: 4

Tipo de Query                       Endpoint                             Taxa Sucesso Taxa Acerto Pos. Média Tempo Médio
----------------------------------------------------------------------------------------------------------------------------------
text_with_formulas_replaced         search-pure-text                     100.0%       66.7%        3.2        0.245s
text_lightly_modified               search-text-with-treated-formulas    100.0%       75.0%        2.8        0.312s
text_semantically_modified          search-text-vector                   100.0%       58.3%        4.1        0.189s
text_natural_language               search-with-text-without-formula...  100.0%       83.3%        2.1        0.567s
```

## Arquivos de Saída

O script gera um arquivo JSON detalhado (`test_results.json` por padrão) contendo:

- Resultados detalhados de cada teste individual
- Estatísticas de performance por tipo de query
- Top-K resultados retornados para cada query
- Tempos de resposta individuais
- Posições onde o post correto foi encontrado

## Estrutura dos Dados de Teste

O arquivo JSON de entrada deve ter a seguinte estrutura:

```json
[
  {
    "post_id": 12345,
    "text_with_formulas_replaced": "Query com fórmulas substituídas...",
    "text_lightly_modified": "Query levemente modificada...",
    "text_semantically_modified": "Query semanticamente modificada...",
    "text_natural_language": "Query em linguagem natural..."
  }
]
```

## Troubleshooting

### Erro de conexão

```
Erro: Não foi possível conectar à API em http://localhost:8000
```

**Solução**: Verifique se o servidor da API está rodando na porta correta.

### Arquivo não encontrado

```
Erro: Arquivo de dados não encontrado: app/assert/questoes_formulas_selecionadas.json
```

**Solução**: Verifique se o caminho para o arquivo de dados está correto.

### Timeout nas requisições

Se as requisições estão dando timeout, você pode ajustar o valor na linha 29 do script:

```python
response = requests.post(url, json=payload, timeout=60)  # aumentar de 30 para 60 segundos
```
