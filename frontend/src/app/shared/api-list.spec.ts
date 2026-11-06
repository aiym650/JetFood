import { getApiListResults } from './api-list';

describe('getApiListResults', () => {
  it('returns unpaginated list responses unchanged', () => {
    const items = [{ id: 1 }];
    expect(getApiListResults(items)).toBe(items);
  });

  it('unwraps paginated API responses', () => {
    const items = [{ id: 1 }];
    expect(getApiListResults({ count: 1, next: null, previous: null, results: items })).toBe(items);
  });
});
