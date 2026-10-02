import { describe, expect, it } from 'vitest';

import { assistantText } from '../../../src/utils/chatStream';
import { historyToMessages } from '../../../src/utils/history';

describe('historyToMessages', () => {
  it('replays each answer as the live stream showed it, without a retracted draft', () => {
    const messages = historyToMessages([
      { role: 'user', text: 'How much?' },
      {
        role: 'assistant',
        events: [
          { type: 'text', text: 'wrong' },
          { type: 'retracted' },
          { type: 'text', text: 'It costs 10.' },
          { type: 'references', references: ['pricing.md'] },
        ],
      },
    ]);

    expect(messages).toEqual([
      { type: 'text', content: { text: 'How much?' }, position: 'right' },
      assistantText('It costs 10.'),
      { type: 'references', content: { references: ['pricing.md'] } },
    ]);
  });
});
