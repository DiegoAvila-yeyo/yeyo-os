import '@testing-library/jest-dom';

// jsdom no implementa scrollIntoView
window.HTMLElement.prototype.scrollIntoView = jest.fn();
