// jsdom has no AnimationEvent, so React would listen for `webkitAnimationEnd` instead of
// `animationend`. Must run before react-dom loads, hence its own module imported first.
if (!('AnimationEvent' in globalThis)) {
  Object.defineProperty(globalThis, 'AnimationEvent', { value: Event });
}
