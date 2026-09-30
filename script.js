'use strict';
const views = {
  onboard: { title: '从第一次启动开始，就很简单。', description: '自动准备运行时、创建默认实例并启动 OpenClaw。', alt: '新版 OpenClaw Launcher 快速上手界面，提供一键安装并启动按钮和功能侧边栏' },
  models: { title: '适合你的模型，就是好模型。', description: '配置在线或本地提供商，测试 API，再应用到实例。', alt: '新版模型切换界面，包含提供商、API 地址、密钥、模型 ID 和 API 测试设置' },
  channels: { title: '在你熟悉的地方，与 OpenClaw 对话。', description: '集中配置聊天频道，缺少插件时直接安装。', alt: '新版频道配置界面，包含 Discord、Telegram、飞书、QQ、钉钉和微信及插件安装入口' },
  llamacpp: { title: '把模型的运行，留在你的电脑上。', description: '选择 GGUF 模型，配置 GPU 层数与端口，启动本地服务。', alt: '新版 LlamaCPP 界面，包含模型文件、多模态投影、端口、GPU 层数和服务控制' },
  plugin: { title: '需要的能力，随时扩展。', description: '按实例查看、安装、更新和卸载插件。', alt: '新版插件管理界面，包含实例选择、插件安装、更新与卸载操作' },
  backup: { title: '给每一次尝试，留一份备份。', description: '创建实例备份，恢复数据并重新安装依赖。', alt: '新版备份管理界面，包含实例备份和备份恢复列表' },
};
const tabs = [...document.querySelectorAll('[role="tab"]')];
const panel = document.getElementById('preview-panel');
const preview = document.getElementById('preview-image');
const previewLink = document.getElementById('preview-image-link');
const dialog = document.getElementById('image-dialog');
const dialogImage = document.getElementById('dialog-image');
function selectView(tab) {
  const key = tab.dataset.view;
  const view = views[key];
  const index = tabs.indexOf(tab);
  tabs.forEach((item) => { const selected = item === tab; item.setAttribute('aria-selected', String(selected)); item.tabIndex = selected ? 0 : -1; });
  panel.setAttribute('aria-labelledby', tab.id);
  preview.src = `./assets/${key}.png`;
  preview.alt = view.alt;
  previewLink.href = preview.src;
  previewLink.setAttribute('aria-label', `放大${tab.textContent}界面截图`);
  document.getElementById('preview-title').textContent = view.title;
  document.getElementById('preview-description').textContent = view.description;
  const count = document.getElementById('preview-count');
  count.textContent = `0${index + 1} / 06`;
  count.setAttribute('aria-label', `第 ${index + 1} 张，共 6 张`);
}
tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => selectView(tab));
  tab.addEventListener('keydown', (event) => {
    let next;
    if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
    if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = tabs.length - 1;
    if (next !== undefined) { event.preventDefault(); selectView(tabs[next]); tabs[next].focus(); }
  });
});
// Preserve the original image link as a fallback without dialog support.
previewLink.addEventListener('click', (event) => {
  if (typeof dialog.showModal !== 'function') return;
  event.preventDefault();
  dialogImage.src = preview.src;
  dialogImage.alt = preview.alt;
  document.getElementById('dialog-caption').textContent = preview.alt;
  dialog.showModal();
});
dialog.addEventListener('click', (event) => {
  const bounds = dialog.getBoundingClientRect();
  if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) dialog.close();
});
// Preload other previews once the main page is ready.
window.addEventListener('load', () => {
  Object.keys(views).filter((key) => key !== 'onboard').forEach((key) => { const image = new Image(); image.src = `./assets/${key}.png`; });
});
