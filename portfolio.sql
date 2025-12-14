CREATE DATABASE IF NOT EXISTS stock_portfolio;
USE stock_portfolio;
CREATE DATABASE IF NOT EXISTS stock_portfolio
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;


-- Users table
CREATE TABLE stock_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Portfolios table
CREATE TABLE portfolios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES stock_users(id) ON DELETE CASCADE
);

-- Holdings table (current position per stock)
CREATE TABLE holdings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    quantity DECIMAL(18,4) NOT NULL,
    avg_cost DECIMAL(18,4) NOT NULL,          -- cost basis per share
    total_cost DECIMAL(18,4) NOT NULL,        -- quantity * avg_cost
    current_price DECIMAL(18,4) DEFAULT 0,
    market_value DECIMAL(18,4) DEFAULT 0,
    unrealized_pl DECIMAL(18,4) DEFAULT 0,
    market_cap BIGINT NULL,
    cap_category ENUM('SMALL', 'MID', 'LARGE') NULL,
    first_buy_date DATE NULL,
    last_buy_date DATE NULL,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
);

-- Transactions / logs
CREATE TABLE transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    holding_id INT NOT NULL,
    tx_type ENUM('BUY', 'SELL') NOT NULL,
    quantity DECIMAL(18,4) NOT NULL,
    price DECIMAL(18,4) NOT NULL,
    tx_date DATE NOT NULL,
    fees DECIMAL(18,4) DEFAULT 0,
    FOREIGN KEY (holding_id) REFERENCES holdings(id) ON DELETE CASCADE
);
