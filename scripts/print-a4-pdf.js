/**
 * print-a4-pdf.js
 * 
 * 基于 Headless CDP (Chrome DevTools Protocol) 的高保真无边距单页 A4 PDF 打印器
 * 适配 A4 标准尺寸：8.27 x 11.69 英寸 (210mm x 297mm)
 */
const fs = require('fs');

async function renderHtmlToA4Pdf(htmlPath, pdfOutputPath) {
  if (!fs.existsSync(htmlPath)) {
    throw new Error(`HTML source file not found: ${htmlPath}`);
  }
  
  cliLog(`[A4-Printer] Rendering HTML to PDF: ${htmlPath} -> ${pdfOutputPath}`);
  const fileUrl = 'file://' + htmlPath;
  await openOrReuseTab(fileUrl, { wait: true, timeout: 20 });
  await wait(1); // 等待字体和 CSS 布局渲染完成

  const pdfResult = await cdp('Page.printToPDF', {
    printBackground: true,
    paperWidth: 8.27,      // A4 宽度 (英寸)
    paperHeight: 11.69,    // A4 高度 (英寸)
    marginTop: 0,
    marginBottom: 0,
    marginLeft: 0,
    marginRight: 0,
    preferCSSPageSize: true
  });

  const pdfBuffer = Buffer.from(pdfResult.data, 'base64');
  fs.writeFileSync(pdfOutputPath, pdfBuffer);
  cliLog(`[A4-Printer] Successfully generated A4 PDF (${pdfBuffer.length} bytes) to: ${pdfOutputPath}`);
}

module.exports = { renderHtmlToA4Pdf };
