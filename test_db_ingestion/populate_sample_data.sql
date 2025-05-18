-- Create customers table
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address VARCHAR(200),
    city VARCHAR(50),
    country VARCHAR(50),
    postal_code VARCHAR(20),
    create_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create products table
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    create_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create orders table
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'Pending',
    total_amount DECIMAL(12, 2),
    shipping_address VARCHAR(200),
    shipping_city VARCHAR(50),
    shipping_country VARCHAR(50),
    shipping_postal_code VARCHAR(20),
    payment_method VARCHAR(50)
);

-- Create order_items table
CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(order_id),
    product_id INTEGER REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL
);

-- Insert sample data into customers table
INSERT INTO customers (first_name, last_name, email, phone, address, city, country, postal_code)
VALUES
    ('John', 'Smith', 'john.smith@example.com', '555-123-4567', '123 Main St', 'New York', 'USA', '10001'),
    ('Jane', 'Doe', 'jane.doe@example.com', '555-234-5678', '456 Park Ave', 'Los Angeles', 'USA', '90001'),
    ('Bob', 'Johnson', 'bob.johnson@example.com', '555-345-6789', '789 Broadway', 'Chicago', 'USA', '60601'),
    ('Alice', 'Williams', 'alice.williams@example.com', '555-456-7890', '321 Elm St', 'Boston', 'USA', '02108'),
    ('Charlie', 'Brown', 'charlie.brown@example.com', '555-567-8901', '654 Oak Rd', 'San Francisco', 'USA', '94101'),
    ('Emma', 'Davis', 'emma.davis@example.com', '555-678-9012', '987 Pine Blvd', 'Seattle', 'USA', '98101'),
    ('Michael', 'Miller', 'michael.miller@example.com', '555-789-0123', '741 Cedar Ln', 'Miami', 'USA', '33101'),
    ('Sophia', 'Wilson', 'sophia.wilson@example.com', '555-890-1234', '852 Birch Dr', 'Dallas', 'USA', '75201'),
    ('Daniel', 'Jones', 'daniel.jones@example.com', '555-901-2345', '963 Maple Ct', 'Houston', 'USA', '77001'),
    ('Olivia', 'Taylor', 'olivia.taylor@example.com', '555-012-3456', '159 Cherry St', 'Philadelphia', 'USA', '19101');

-- Insert sample data into products table
INSERT INTO products (product_name, description, category, price, stock_quantity)
VALUES
    ('Laptop', 'High-performance laptop with 16GB RAM and 512GB SSD', 'Electronics', 1299.99, 50),
    ('Smartphone', 'Latest model with 128GB storage and dual camera', 'Electronics', 899.99, 100),
    ('Wireless Headphones', 'Noise-cancelling Bluetooth headphones', 'Electronics', 199.99, 75),
    ('Coffee Maker', 'Programmable coffee maker with built-in grinder', 'Kitchen', 149.99, 30),
    ('Blender', 'High-powered blender for smoothies and soups', 'Kitchen', 79.99, 45),
    ('Athletic Shoes', 'Running shoes with cushioned soles', 'Clothing', 89.99, 60),
    ('Winter Jacket', 'Waterproof and insulated winter jacket', 'Clothing', 159.99, 35),
    ('Yoga Mat', 'Non-slip yoga mat with carrying strap', 'Fitness', 29.99, 80),
    ('Dumbbells Set', 'Set of adjustable dumbbells', 'Fitness', 249.99, 25),
    ('Indoor Plant', 'Low-maintenance indoor plant in decorative pot', 'Home', 34.99, 40),
    ('Desk Lamp', 'LED desk lamp with adjustable brightness', 'Home', 49.99, 55),
    ('Backpack', 'Durable backpack with laptop compartment', 'Accessories', 59.99, 65),
    ('Watch', 'Stainless steel analog watch', 'Accessories', 129.99, 40),
    ('Sunglasses', 'UV-protective polarized sunglasses', 'Accessories', 79.99, 70),
    ('Water Bottle', 'Insulated stainless steel water bottle', 'Accessories', 24.99, 90);

-- Insert sample data into orders table
INSERT INTO orders (customer_id, order_date, status, total_amount, shipping_address, shipping_city, shipping_country, shipping_postal_code, payment_method)
VALUES
    (1, '2025-01-05 10:30:00', 'Completed', 1499.97, '123 Main St', 'New York', 'USA', '10001', 'Credit Card'),
    (2, '2025-01-10 14:45:00', 'Completed', 979.98, '456 Park Ave', 'Los Angeles', 'USA', '90001', 'PayPal'),
    (3, '2025-01-15 09:15:00', 'Shipped', 349.98, '789 Broadway', 'Chicago', 'USA', '60601', 'Credit Card'),
    (4, '2025-01-20 16:20:00', 'Processing', 199.99, '321 Elm St', 'Boston', 'USA', '02108', 'Debit Card'),
    (5, '2025-01-25 11:10:00', 'Completed', 404.95, '654 Oak Rd', 'San Francisco', 'USA', '94101', 'Credit Card'),
    (6, '2025-01-30 13:25:00', 'Shipped', 159.99, '987 Pine Blvd', 'Seattle', 'USA', '98101', 'PayPal'),
    (7, '2025-02-05 15:30:00', 'Processing', 299.97, '741 Cedar Ln', 'Miami', 'USA', '33101', 'Credit Card'),
    (8, '2025-02-10 10:45:00', 'Pending', 129.99, '852 Birch Dr', 'Dallas', 'USA', '75201', 'Debit Card'),
    (9, '2025-02-15 12:50:00', 'Shipped', 259.98, '963 Maple Ct', 'Houston', 'USA', '77001', 'Credit Card'),
    (10, '2025-02-20 14:15:00', 'Completed', 284.97, '159 Cherry St', 'Philadelphia', 'USA', '19101', 'PayPal'),
    (1, '2025-03-01 09:30:00', 'Shipped', 149.99, '123 Main St', 'New York', 'USA', '10001', 'Credit Card'),
    (3, '2025-03-05 16:45:00', 'Completed', 79.99, '789 Broadway', 'Chicago', 'USA', '60601', 'PayPal'),
    (5, '2025-03-10 11:20:00', 'Processing', 329.98, '654 Oak Rd', 'San Francisco', 'USA', '94101', 'Credit Card'),
    (7, '2025-03-15 13:40:00', 'Shipped', 114.98, '741 Cedar Ln', 'Miami', 'USA', '33101', 'Debit Card'),
    (9, '2025-03-20 15:55:00', 'Pending', 249.99, '963 Maple Ct', 'Houston', 'USA', '77001', 'Credit Card');

-- Insert sample data into order_items table
INSERT INTO order_items (order_id, product_id, quantity, unit_price, total_price)
VALUES
    (1, 1, 1, 1299.99, 1299.99),
    (1, 3, 1, 199.98, 199.98),
    (2, 2, 1, 899.99, 899.99),
    (2, 3, 1, 79.99, 79.99),
    (3, 4, 1, 149.99, 149.99),
    (3, 5, 1, 199.99, 199.99),
    (4, 3, 1, 199.99, 199.99),
    (5, 6, 1, 89.99, 89.99),
    (5, 7, 1, 159.99, 159.99),
    (5, 10, 1, 34.99, 34.99),
    (5, 11, 1, 49.99, 49.99),
    (5, 15, 1, 69.99, 69.99),
    (6, 7, 1, 159.99, 159.99),
    (7, 9, 1, 249.99, 249.99),
    (7, 15, 2, 24.99, 49.98),
    (8, 13, 1, 129.99, 129.99),
    (9, 8, 1, 29.99, 29.99),
    (9, 9, 1, 229.99, 229.99),
    (10, 11, 1, 49.99, 49.99),
    (10, 12, 1, 59.99, 59.99),
    (10, 15, 1, 24.99, 24.99),
    (10, 10, 1, 34.99, 34.99),
    (10, 14, 1, 79.99, 114.98),
    (11, 4, 1, 149.99, 149.99),
    (12, 5, 1, 79.99, 79.99),
    (13, 7, 1, 159.99, 159.99),
    (13, 9, 1, 249.99, 169.99),
    (14, 8, 1, 29.99, 29.99),
    (14, 15, 1, 24.99, 24.99),
    (14, 14, 1, 59.99, 59.99),
    (15, 9, 1, 249.99, 249.99);

-- Create a sales_summary view for testing views
CREATE VIEW sales_summary AS
SELECT 
    p.category,
    SUM(oi.quantity) as total_units_sold,
    SUM(oi.total_price) as total_revenue
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
GROUP BY p.category
ORDER BY total_revenue DESC;

-- Create a customer_order_summary view
CREATE VIEW customer_order_summary AS
SELECT 
    c.customer_id,
    c.first_name || ' ' || c.last_name as customer_name,
    COUNT(o.order_id) as total_orders,
    SUM(o.total_amount) as total_spent
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, customer_name
ORDER BY total_spent DESC NULLS LAST;
