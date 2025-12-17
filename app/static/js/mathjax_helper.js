function renderMarkdownWithMath(md, targetSelector) {
  // 去除 YAML Frontmatter
  md = (md || '').replace(/^---\s*[\s\S]*?\s*---\s*/, '');

  const el = document.querySelector(targetSelector);
  if (!el) return;

  // 提前提取数学公式块，避免 marked 将 \\ 转为 <br> 或 \
  const blocks = [];
  const placeholder = (i) => `@@MATH_BLOCK_${i}@@`;
  let protectedMd = md;

  // 1. Protect $$...$$
  protectedMd = protectedMd.replace(/\$\$([\s\S]*?)\$\$/g, (match) => {
    blocks.push(match);
    return placeholder(blocks.length - 1);
  });

  // 2. Protect \[...\]
  protectedMd = protectedMd.replace(/\\\[([\s\S]*?)\\\]/g, (match) => {
    blocks.push(match);
    return placeholder(blocks.length - 1);
  });

  // 3. Protect \begin{env}...\end{env}
  protectedMd = protectedMd.replace(/\\begin\{([a-z\*]+)\}[\s\S]*?\\end\{\1\}/g, (match) => {
    blocks.push(match);
    return placeholder(blocks.length - 1);
  });

  marked.setOptions({
    gfm: true,
    breaks: true,
    mangle: false,
    headerIds: false
  });

  let html = DOMPurify.sanitize(marked.parse(protectedMd), {
    USE_PROFILES: { html: true }
  });

  // 把占位符替换回原始 TeX 块，使用 div 确保块级显示和居中
  blocks.forEach((tex, idx) => {
    html = html.replace(
      placeholder(idx),
      `<div class="math-block">${tex}</div>`
    );
  });

  el.innerHTML = html;

  if (window.hljs) {
    hljs.highlightAll();
  }

  const tryTypeset = () => {
    if (window.MathJax && window.MathJax.typesetPromise) {
      MathJax.typesetPromise([el]).then(() => {
        // MathJax 渲染完成后，确保 math-block 内的元素居中
        const mathBlocks = el.querySelectorAll('.math-block');
        mathBlocks.forEach(block => {
          block.style.textAlign = 'center';
          // 确保 MathJax 渲染的容器也居中
          // const mjxContainers = block.querySelectorAll('mjx-container');
          // mjxContainers.forEach(container => {
          //   container.style.display = 'inline-block';
          //   container.style.margin = '0 auto';
          // });
        });
      }).catch(() => {});
    } else {
      setTimeout(tryTypeset, 80);
    }
  };
  tryTypeset();
}
