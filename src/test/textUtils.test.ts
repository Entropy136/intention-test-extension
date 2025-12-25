import * as assert from 'assert';
import { isGenTestPrompt, isCodeQLPrompt, shouldGenTestPrompt, extractRefTestCode, extractGenTestCode, langSuffix, detectCodeLang } from '../textUtils';

suite('textUtils', () => {
    suite('isGenTestPrompt', () => {
        test('returns true when message contains instruction marker', () => {
            const msg = 'Some text Instruction for this step: do something';
            assert.strictEqual(isGenTestPrompt(msg), true);
        });

        test('returns false when message does not contain marker', () => {
            const msg = 'Just a regular message';
            assert.strictEqual(isGenTestPrompt(msg), false);
        });
    });

    suite('isCodeQLPrompt', () => {
        test('returns true when message starts with The required', () => {
            const msg = 'The required dependencies are...';
            assert.strictEqual(isCodeQLPrompt(msg), true);
        });

        test('returns false when message does not start with marker', () => {
            const msg = 'Some other message The required';
            assert.strictEqual(isCodeQLPrompt(msg), false);
        });
    });

    suite('shouldGenTestPrompt', () => {
        test('returns true for gen test prompt', () => {
            const msg = 'Instruction for this step: test';
            assert.strictEqual(shouldGenTestPrompt(msg), true);
        });

        test('returns true for codeql prompt', () => {
            const msg = 'The required files...';
            assert.strictEqual(shouldGenTestPrompt(msg), true);
        });

        test('returns false for neither', () => {
            const msg = 'Regular message';
            assert.strictEqual(shouldGenTestPrompt(msg), false);
        });
    });

    suite('extractRefTestCode', () => {
        test('extracts code from referable test case section', () => {
            const msg = `# Referable Test Case
\`\`\`java
public class Test {}
\`\`\``;
            const result = extractRefTestCode(msg);
            assert.ok(result);
            assert.ok(result.includes('public class Test'));
        });

        test('returns undefined when no match', () => {
            const msg = 'No code here';
            assert.strictEqual(extractRefTestCode(msg), undefined);
        });
    });

    suite('extractGenTestCode', () => {
        test('extracts code from generic code block', () => {
            const msg = `Some text
\`\`\`
def hello():
    pass
\`\`\``;
            const result = extractGenTestCode(msg);
            assert.ok(result);
            assert.ok(result.includes('def hello()'));
        });

        test('returns undefined for QUERY blocks', () => {
            const msg = `\`\`\`
# QUERY: something
\`\`\``;
            assert.strictEqual(extractGenTestCode(msg), undefined);
        });
    });

    suite('langSuffix', () => {
        test('returns .java for java', () => {
            assert.strictEqual(langSuffix('java'), '.java');
        });

        test('returns empty string for unknown lang', () => {
            assert.strictEqual(langSuffix('unknown'), '');
        });

        test('returns empty string for python', () => {
            assert.strictEqual(langSuffix('python'), '');
        });
    });

    suite('detectCodeLang', () => {
        test('always returns java', () => {
            assert.strictEqual(detectCodeLang('any code'), 'java');
        });
    });
});
