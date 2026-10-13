// Execute the actual interpreter logic embedded in the standalone web application.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync(new URL('../web/index.html', import.meta.url), 'utf8');
const start = html.indexOf('function decimal(');
const stop = html.indexOf('function appendLine(');
assert.ok(start > 0 && stop > start, 'Web interpreter function boundaries found');
const context = {};
vm.runInNewContext(html.slice(start, stop), context);
const base = {
  organism: 'Synthetic organism',
  antimicrobial: 'Illustrative antimicrobial',
  breakpoint_version: 'ILLUSTRATIVE ONLY',
  s_le: '1', r_gt: '8', atu_low: '', atu_high: ''
};
for (const [mic, expected] of Object.entries({
  '1': 'S', '2': 'I', '8': 'I', '16': 'R',
  '<=1': 'S', '>8': 'R', '>=8': 'UNDETERMINED',
  '<2': 'UNDETERMINED', '<=16': 'UNDETERMINED'
})) {
  assert.equal(context.interpret({...base, mic}).classification, expected, mic);
}
assert.equal(context.interpret({...base, mic: '4', atu_low: '2', atu_high: '4'}).classification, 'ATU');
assert.throws(() => context.interpret({...base, mic: 'NaN'}));
assert.throws(() => context.interpret({...base, mic: '4', atu_low: '2'}));
console.log('Standalone browser interpreter checks passed.');
