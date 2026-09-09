/**
 * feishu-crawler.js
 * 
 * 飞书招聘 (Jobs Feishu) 系统在招岗位与规则提取辅助脚本
 */
async function extractFeishuJobs() {
  cliLog('[Feishu-Crawler] Extracting job listing from DOM...');
  const jobs = await js(`(() => {
    const list = [];
    const items = document.querySelectorAll('.position-card, .list-item, [class*="positionItem"]');
    items.forEach(el => {
      const title = el.querySelector('[class*="title"], h3, h4')?.innerText?.trim();
      const location = el.querySelector('[class*="location"], [class*="city"]')?.innerText?.trim();
      const department = el.querySelector('[class*="department"]')?.innerText?.trim();
      const desc = el.querySelector('[class*="desc"], [class*="requirement"]')?.innerText?.trim();
      if (title) {
        list.push({ title, location, department, desc });
      }
    });
    return list;
  })()`);
  cliLog(`[Feishu-Crawler] Successfully extracted ${jobs.length} jobs.`);
  return jobs;
}

module.exports = { extractFeishuJobs };
