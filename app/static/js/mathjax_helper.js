function renderMarkdownWithMath(md, targetSelector) {
  const el = document.querySelector(targetSelector);
  if (!el) return;

  // 提前提取 $$...$$ 块，避免 marked 将 \\ 转为 <br>
  const blocks = [];
  const placeholder = (i) => `@@MATH_BLOCK_${i}@@`;
  const protectedMd = (md || '').replace(/\$\$([\s\S]*?)\$\$/g, (_, m, i) => {
    blocks.push(m);
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

  // 把占位符替换回原始 TeX 块，包裹 span 以便 MathJax 处理
  blocks.forEach((tex, idx) => {
    html = html.replace(
      placeholder(idx),
      `<span class="math-block">$$${tex}$$</span>`
    );
  });

  el.innerHTML = html;

  if (window.hljs) {
    hljs.highlightAll();
  }

  const tryTypeset = () => {
    if (window.MathJax && window.MathJax.typesetPromise) {
      MathJax.typesetPromise([el]).catch(() => {});
    } else {
      setTimeout(tryTypeset, 80);
    }
  };
  tryTypeset();
}

