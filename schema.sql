-- Inventory DB schema for Inventory Management System
CREATE DATABASE IF NOT EXISTS inventorydb;
USE inventorydb;

CREATE TABLE IF NOT EXISTS products (
  id INT AUTO_INCREMENT PRIMARY KEY,
  sku VARCHAR(64) UNIQUE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  category VARCHAR(120),
  quantity INT DEFAULT 0,
  reorder_level INT DEFAULT 0,
  price DECIMAL(10,2) DEFAULT 0.00,
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT INTO products (sku, name, description, category, quantity, reorder_level, price) VALUES
('SKU-1001','Wireless Mouse','Optical wireless mouse','Peripherals',50,10,399.00),
('SKU-1002','USB Keyboard','Compact USB keyboard','Peripherals',30,5,299.00),
('SKU-2001','14-inch Laptop','Core i3, 8GB RAM, 256GB SSD','Computers',12,3,28999.00),
('SKU-3001','HDMI Cable 2m','High-speed HDMI cable','Accessories',100,20,199.00);
