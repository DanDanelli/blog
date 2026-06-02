# Design do Blog Portfólio - Hugo + Blowfish

**Data:** 2026-06-02  
**Autor:** Gemini CLI  
**Status:** Validado pelo Usuário

## 1. Visão Geral
Criação de um blog/portfólio técnico focado em exibir projetos de forma visual (grade) e artigos de estudo, utilizando o gerador de sites estáticos Hugo e o tema Blowfish, hospedado no GitHub Pages.

## 2. Arquitetura de Conteúdo
O site será dividido em dois tipos principais de conteúdo:

- **Projetos (`content/projects/`)**: Exibidos em formato de grade visual (cards) na página inicial. Cada projeto terá uma imagem de capa (`featured.*`) e metadados específicos.
- **Artigos/Estudos (`content/posts/`)**: Lista cronológica de textos técnicos e tutoriais.

### Taxonomia
- **Tags**: Sistema global de tags para conectar projetos e artigos por tecnologia (ex: Python, React, AWS).

## 3. Design Visual
- **Tema**: Blowfish (Showcase Modular).
- **Layout Home**: Grade de cards com imagens e resumos.
- **Funcionalidades**: Modo escuro nativo, menu de navegação simplificado (Sobre, Projetos, Artigos, Contato).

## 4. Fluxo de Deploy
- **Plataforma**: GitHub Pages.
- **Automação**: GitHub Actions.
- **Processo**: O build será disparado automaticamente a cada `git push` na branch principal, gerando e publicando os arquivos estáticos.

## 5. Estrutura de Pastas Esperada
```text
.
├── archetypes/
├── assets/
├── config/
│   └── _default/
│       ├── hugo.toml
│       ├── menus.toml
│       └── params.toml
├── content/
│   ├── projects/
│   ├── posts/
│   └── _index.md
├── static/
└── themes/
    └── blowfish/
```
