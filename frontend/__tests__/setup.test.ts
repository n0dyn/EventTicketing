import '@testing-library/jest-dom'

/**
 * Basic test to verify Jest setup is working
 */
describe('Jest Setup', () => {
  it('should be able to run tests', () => {
    expect(true).toBe(true)
  })

  it('should have access to DOM testing library matchers', () => {
    const element = document.createElement('div')
    element.textContent = 'Hello World'
    expect(element).toHaveTextContent('Hello World')
  })
})