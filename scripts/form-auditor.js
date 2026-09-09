/**
 * form-auditor.js
 * 
 * ATS 网页在线表单全字段深度核验与结构化项目补全辅助工具
 */
async function auditOnlineForm() {
  cliLog('[Form-Auditor] Scanning ATS form fields...');
  const auditReport = await js(`(() => {
    const inputs = Array.from(document.querySelectorAll('input, textarea, select'));
    const fields = inputs.map(i => {
      const label = i.closest('label')?.innerText || i.placeholder || i.name || i.id;
      const val = i.value || i.innerText;
      const isRequired = i.required || !!i.closest('[class*="required"]');
      return { label: label?.replace(/\\s+/g, ' ').trim(), value: val?.trim(), isRequired };
    });
    return fields.filter(f => f.label);
  })()`);
  
  cliLog(`[Form-Auditor] Found ${auditReport.length} form inputs.`);
  return auditReport;
}

module.exports = { auditOnlineForm };
