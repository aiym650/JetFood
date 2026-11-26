// Keep the DOM test suite within the memory available on developer laptops.
export default { test: { maxWorkers: 2, ...(process.env.JETFOOD_TEST_REPORT ? { reporters: ['default', 'json'], outputFile: { json: process.env.JETFOOD_TEST_REPORT } } : {}) } };
