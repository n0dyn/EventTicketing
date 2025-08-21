/**
 * Simple tests to verify Jest configuration is working
 */

describe('Basic Jest Setup', () => {
  it('should run simple tests', () => {
    expect(2 + 2).toBe(4)
    expect('hello').toMatch(/hello/)
  })

  it('should handle async tests', async () => {
    const promise = Promise.resolve(42)
    await expect(promise).resolves.toBe(42)
  })

  it('should mock functions', () => {
    const mockFn = jest.fn()
    mockFn('test')
    expect(mockFn).toHaveBeenCalledWith('test')
  })
})