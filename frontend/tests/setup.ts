import './polyfills';
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll } from 'vitest';

import { server } from './server';

Element.prototype.scrollIntoView = () => {};

// jsdom has no modal dialogs: showModal and close only toggle `open`, and Escape sends
// the top dialog `cancel`, as a browser does wherever focus is.
HTMLDialogElement.prototype.showModal = function () {
  this.setAttribute('open', '');
};
HTMLDialogElement.prototype.close = function () {
  this.removeAttribute('open');
};
document.addEventListener('keydown', (e) => {
  const top = [...document.querySelectorAll('dialog[open]')].at(-1);
  if (e.key === 'Escape' && top) top.dispatchEvent(new Event('cancel', { cancelable: true }));
});

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());
