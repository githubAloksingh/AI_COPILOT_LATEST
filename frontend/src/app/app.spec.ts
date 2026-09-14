import '@angular/compiler';
import { describe, it, expect } from 'vitest';
import { App } from './app';

describe('App', () => {
  it('should instantiate the app component', () => {
    const app = new App();
    expect(app).toBeTruthy();
  });
});
