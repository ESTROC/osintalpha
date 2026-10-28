const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync('static/console_panels.js','utf8');
const context={window:{}};vm.runInNewContext(src,context);
const render=context.window.OSINTAlphaPanels.originPanel;
const result=render({duplicateOriginGroups:[{sourceCount:2,originKeySha256:'a'.repeat(64),
  classification:'<img src=x onerror=alert(1)>',providers:['example']} ]},{items:[{status:'todo'}]});
assert.ok(result.includes('&lt;img'));assert.ok(!result.includes('<img'));
assert.ok(result.includes('data-tab="tasks"'));
console.log('PASS source panels escape untrusted provenance');