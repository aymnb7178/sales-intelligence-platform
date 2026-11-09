-- Schema for the SYNTHETIC retail dataset.
CREATE TABLE customers (
    customer_id         INTEGER PRIMARY KEY,
    customer_code       TEXT NOT NULL UNIQUE,
    region              TEXT NOT NULL,
    acquisition_channel TEXT NOT NULL,
    signup_date         TEXT NOT NULL
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    category   TEXT NOT NULL,
    unit_cost  REAL NOT NULL CHECK (unit_cost >= 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0)
);

CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers (customer_id),
    order_date  TEXT NOT NULL,
    channel     TEXT NOT NULL
);

CREATE TABLE order_items (
    item_id    INTEGER PRIMARY KEY,
    order_id   INTEGER NOT NULL REFERENCES orders (order_id),
    product_id INTEGER NOT NULL REFERENCES products (product_id),
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL,
    discount   REAL NOT NULL CHECK (discount >= 0 AND discount < 1)
);

CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX idx_orders_date ON orders (order_date);
CREATE INDEX idx_items_order ON order_items (order_id);
CREATE INDEX idx_items_product ON order_items (product_id);
