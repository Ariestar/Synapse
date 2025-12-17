## [2025-12-17] Notes 页面重构
- **核心概念**: 将 `notes.html` 的列表渲染与筛选逻辑从 Vanilla JS 迁移至 Alpine.js 组件 `notesPage()`，实现更紧密的 MVVM 绑定。
- **实现细节/语法**: 
    - `notesPage()`: 维护 `notes` 数组与 `searchQuery` 状态，提供 `filteredNotes` 计算属性实现实时筛选（支持标题/标签/路径/内容）。
    - `x-for`: 替代手动 DOM 操作渲染笔记卡片，使用 `<template x-for="note in filteredNotes">`。
    - `debounce`: 输入框使用 `x-model.debounce.300ms` 自动防抖。
    - `getSnippet`: 新增前端助手函数，自动去除 YAML frontmatter 和 Markdown 符号，展示正文摘要。
- **避坑/注意**: `newNoteModal` 创建成功后通过 `window.dispatchEvent(new CustomEvent('reload-notes'))` 通知列表刷新，解耦组件通信。
