# O caminho do dinheiro

## O que o grafo mostra

`fundo_eleitoral.fluxos` transforma receitas declaradas de FEFC em arestas:

```text
diretório nacional -> diretório estadual/distrital -> candidaturas por UF e cargo
```

Cada aresta vai do diretório identificado como doador ao destino que declarou a
receita. Os nós de diretório são agrupados por partido, esfera e UF; o destino
de candidaturas, por partido, UF e cargo. O comando padrão mostra ambos os
tipos de aresta; `--somente-diretorios` ou `--somente-candidaturas` isola uma
etapa.

Quando o CNPJ do diretório que declara a receita é o mesmo do doador, o TSE
está registrando a entrada do fundo na própria direção, e não uma transferência
para ela mesma. O grafo mostra esse caso como `fundo_especial -> diretório`,
evitando um autoelo contábil enganoso.

```bash
python -m fundo_eleitoral.fluxos --ano 2022 --partido PDT --minimo-milhoes 1
python -m fundo_eleitoral.fluxos --ano 2022 --somente-diretorios
python -m fundo_eleitoral.fluxos --ano 2022 --partido PDT --formato dot > pdt.dot
```

O formato `dot` pode ser aberto pelo Graphviz e mantém o valor e a quantidade
de lançamentos no rótulo de cada aresta.

## O que ele não afirma

O grafo é de **fluxos declarados**, não de dinheiro novo em cada nó. Uma mesma
quantia transferida de nacional para estadual e depois a uma candidatura gera
duas arestas corretas, mas somá-las duplicaria o recurso. Para isso, o relatório
lista arestas individualmente e não publica um "total do grafo".

Também não é possível reconstruir uma trilha unitária até a candidatura: os
arquivos de prestação de contas não oferecem um identificador transacional
comum entre a receita declarada pelo diretório e a receita declarada pela
candidatura. O resultado aponta canais e volumes, não prova que uma entrada
específica financiou uma saída específica.

## Critérios

- Apenas `FUNDO ESPECIAL` entra.
- A origem precisa ser identificada pelo TSE como diretório partidário.
- Repasses candidatura -> candidatura ficam fora: pertencem a outro tipo de
  fluxo e duplicam FEFC já repassado pelo partido ([ADR-009](decisoes.md#adr-009--repasse-entre-candidaturas-fica-fora-da-concentração)).
- `Federal (Estadual/Distrital)` é normalizado para `estadual_distrital`;
  nacional e municipal mantêm suas próprias escalas.
