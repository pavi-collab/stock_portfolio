# stock_portfolio
Stock portfolio web app for students and beginners to track holdings, live prices, P&amp;L, tax classification, and risk categories using Flask, MySQL, and yFinance.
# Stock Portfolio Management Web App

This project is a **stock portfolio management website** built with **Python, Flask, MySQL, SQLAlchemy, and yFinance**.  

After registering and logging in, a user can:

- Create one or more **portfolios**
- Add **holdings** for each portfolio (stock symbol, quantity, average cost, first buy date)
- View **total cost, current market value, and profit/loss** for each stock and for the whole portfolio
- Keep a **log of transactions** (BUY/SELL with date, quantity, price and fees)

The Webapp also:

- Uses the **yFinance** library to fetch **live prices** and **market cap** for each stock
- Classifies each holding as **short-term** or **long-term** based on the first buy date (tax view)
- Groups stocks into **small-cap, mid-cap, and large-cap** based on market capitalization
- Highlights **stocks making money vs. not making money**, and shows how the **overall portfolio** is performing
- Implements full **CRUD operations with search** (search portfolios by name and holdings by stock symbol)
- Includes **user authentication and session management** (register, login, logout, protected routes)

The main goal of this project is to demonstrate:

- How to build a complete Flask web application with a MySQL backend
- How to integrate an external API (yFinance) into a web app
- How basic portfolio metrics, profit & loss, risk categories, and tax classifications work in a simple, educational interface.
