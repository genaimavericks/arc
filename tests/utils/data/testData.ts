/**
 * Test data for RSW web GUI automation tests
 */

export const users = {
  admin: {
    username: 'admin@example.com',
    password: 'admin123',
    role: 'admin'
  },
  regular: {
    username: 'user@example.com',
    password: 'user123',
    role: 'user'
  },
  readonly: {
    username: 'readonly@example.com',
    password: 'readonly123',
    role: 'readonly'
  }
};

export const dataSets = {
  telecom: {
    name: 'Telecom Customer Dataset',
    path: '/datasets/telecom_customers.csv',
    rowCount: 1000,
    columns: ['customer_id', 'name', 'age', 'subscription_type', 'monthly_charge']
  },
  financial: {
    name: 'Financial Transactions',
    path: '/datasets/financial_transactions.csv',
    rowCount: 2500,
    columns: ['transaction_id', 'date', 'amount', 'category', 'vendor']
  }
};

export const knowledgeGraphs = {
  telecomNetwork: {
    name: 'Telecom Network Graph',
    nodeCount: 150,
    edgeCount: 250,
    nodeTypes: ['Customer', 'Service', 'Device']
  },
  supplyChain: {
    name: 'Supply Chain Graph',
    nodeCount: 200,
    edgeCount: 350,
    nodeTypes: ['Supplier', 'Product', 'Warehouse', 'Customer']
  }
};
