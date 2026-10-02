/**
 * react-markdown doesn't say whether a `code` node is inline or a fenced block, so this
 * tells them apart the way the content itself does: a fenced block's text always contains
 * a newline, an inline span never does.
 */
export function isFencedCodeBlock(children: unknown): boolean {
  return typeof children === 'string' && children.includes('\n');
}
