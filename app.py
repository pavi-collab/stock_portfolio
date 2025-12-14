from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date
import yfinance as yf

app = Flask(__name__)

# DB CONFIG root user with password: Happyfish@31  (@ must be URL-encoded as %40)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mysql+pymysql://root:Happyfish%4031@localhost/stock_portfolio"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "dev-secret-key"  
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "stock_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    portfolios = db.relationship("Portfolio", backref="user", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Portfolio(db.Model):
    __tablename__ = "portfolios"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("stock_users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    holdings = db.relationship(
        "Holding",
        backref="portfolio",
        lazy=True,
        cascade="all, delete-orphan",
    )


class Holding(db.Model):
    __tablename__ = "holdings"

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=False)

    symbol = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Numeric(18, 4), nullable=False)
    avg_cost = db.Column(db.Numeric(18, 4), nullable=False)
    total_cost = db.Column(db.Numeric(18, 4), nullable=False)

    current_price = db.Column(db.Numeric(18, 4), default=0)
    market_value = db.Column(db.Numeric(18, 4), default=0)
    unrealized_pl = db.Column(db.Numeric(18, 4), default=0)

    market_cap = db.Column(db.BigInteger, nullable=True)
    cap_category = db.Column(
        db.Enum("SMALL", "MID", "LARGE", name="cap_category_enum"),
        nullable=True,
    )

    first_buy_date = db.Column(db.Date, nullable=True)
    last_buy_date = db.Column(db.Date, nullable=True)

    transactions = db.relationship(
        "Transaction",
        backref="holding",
        lazy=True,
        cascade="all, delete-orphan",
    )

    @property
    def tax_class(self):
        if not self.first_buy_date:
            return None
        days = (date.today() - self.first_buy_date).days
        return "LONG" if days >= 365 else "SHORT"


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    holding_id = db.Column(db.Integer, db.ForeignKey("holdings.id"), nullable=False)

    tx_type = db.Column(
        db.Enum("BUY", "SELL", name="tx_type_enum"),
        nullable=False,
    )
    quantity = db.Column(db.Numeric(18, 4), nullable=False)
    price = db.Column(db.Numeric(18, 4), nullable=False)
    tx_date = db.Column(db.Date, nullable=False)
    fees = db.Column(db.Numeric(18, 4), default=0)


def current_user():
    """Return the logged-in User object or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def login_required(f):
    """Decorator that requires a *valid* logged-in user."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        user = User.query.get(user_id)
        if user is None:
            
            session.clear()
            flash("Your session has expired. Please log in again.", "warning")
            return redirect(url_for("login"))
       
        return f(*args, **kwargs)
    return wrapper


@app.template_filter("datefmt")
def format_date(value, fmt="%Y-%m-%d"):
    if not value:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime(fmt)
    return str(value)


@app.template_filter("money")
def format_money(value):
    if value is None:
        return "-"
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def classify_cap(market_cap):
    if market_cap is None:
        return None
    if market_cap < 2_000_000_000:
        return "SMALL"
    if market_cap < 10_000_000_000:
        return "MID"
    return "LARGE"


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))

        if User.query.filter(
            (User.username == username) | (User.email == email)
        ).first():
            flash("Username or email already exists.", "danger")
            return redirect(url_for("register"))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash("Logged in successfully.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    user = current_user()
   
    portfolios_list = Portfolio.query.filter_by(user_id=user.id).all()

    summaries = []
    for p in portfolios_list:
        holdings = p.holdings
        total_cost = sum((h.total_cost or 0) for h in holdings)
        total_value = sum((h.market_value or 0) for h in holdings)
        total_pl = total_value - total_cost
        summaries.append(
            {
                "portfolio": p,
                "total_cost": total_cost,
                "total_value": total_value,
                "total_pl": total_pl,
            }
        )

    return render_template("dashboard.html", portfolios=summaries)



@app.route("/portfolios")
@login_required
def portfolios():
    user = current_user()
    portfolios_list = Portfolio.query.filter_by(user_id=user.id).all()
    return render_template("portfolios.html", portfolios=portfolios_list)


@app.route("/portfolios/add", methods=["GET", "POST"])
@login_required
def add_portfolio():
    user = current_user()
    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Portfolio name is required.", "danger")
            return redirect(url_for("add_portfolio"))

        p = Portfolio(user_id=user.id, name=name, description=description)
        db.session.add(p)
        db.session.commit()
        flash("Portfolio created.", "success")
        return redirect(url_for("portfolios"))

    return render_template("portfolio_detail.html", mode="add")


@app.route("/portfolios/<int:portfolio_id>")
@login_required
def portfolio_detail(portfolio_id):
    user = current_user()
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=user.id).first_or_404()
    holdings = portfolio.holdings

    making_money = [h for h in holdings if (h.unrealized_pl or 0) > 0]
    losing_money = [h for h in holdings if (h.unrealized_pl or 0) <= 0]

    return render_template(
        "portfolio_detail.html",
        mode="view",
        portfolio=portfolio,
        holdings=holdings,
        making_money=making_money,
        losing_money=losing_money,
    )


@app.route("/search", methods=["GET"])
@login_required
def search():
    user = current_user()
    query = request.args.get("q", "").strip()

    portfolios = []
    holdings = []

    if query:
      
        portfolios = Portfolio.query.filter(
            Portfolio.user_id == user.id,
            Portfolio.name.ilike(f"%{query}%")
        ).all()

        holdings = (
            Holding.query
            .join(Portfolio)
            .filter(
                Portfolio.user_id == user.id,
                Holding.symbol.ilike(f"%{query}%")
            )
            .all()
        )

    return render_template(
        "search.html",
        q=query,
        portfolios=portfolios,
        holdings=holdings,
    )

@app.route("/portfolios/<int:portfolio_id>/edit", methods=["GET", "POST"])
@login_required
def edit_portfolio(portfolio_id):
    user = current_user()
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=user.id).first_or_404()

    if request.method == "POST":
        portfolio.name = request.form["name"].strip()
        portfolio.description = request.form.get("description", "").strip()
        db.session.commit()
        flash("Portfolio updated.", "success")
        return redirect(url_for("portfolio_detail", portfolio_id=portfolio.id))

    return render_template("portfolio_detail.html", mode="edit", portfolio=portfolio)


@app.route("/portfolios/<int:portfolio_id>/delete", methods=["POST"])
@login_required
def delete_portfolio(portfolio_id):
    user = current_user()
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=user.id).first_or_404()
    db.session.delete(portfolio)
    db.session.commit()
    flash("Portfolio deleted.", "info")
    return redirect(url_for("portfolios"))


@app.route("/portfolios/<int:portfolio_id>/holdings/add", methods=["GET", "POST"])
@login_required
def add_holding(portfolio_id):
    user = current_user()
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=user.id).first_or_404()

    if request.method == "POST":
        symbol = request.form["symbol"].strip().upper()
        quantity = float(request.form["quantity"])
        avg_cost = float(request.form["avg_cost"])
        first_buy_date_str = request.form.get("first_buy_date")

        first_buy_date = None
        if first_buy_date_str:
            first_buy_date = datetime.strptime(first_buy_date_str, "%Y-%m-%d").date()

        total_cost = quantity * avg_cost

        h = Holding(
            portfolio_id=portfolio.id,
            symbol=symbol,
            quantity=quantity,
            avg_cost=avg_cost,
            total_cost=total_cost,
            first_buy_date=first_buy_date,
        )
        db.session.add(h)
        db.session.commit()
        flash("Holding added.", "success")
        return redirect(url_for("portfolio_detail", portfolio_id=portfolio.id))

    return render_template("holding_form.html", mode="add", portfolio=portfolio)


@app.route("/holdings/<int:holding_id>/edit", methods=["GET", "POST"])
@login_required
def edit_holding(holding_id):
    user = current_user()
    holding = (
        Holding.query.join(Portfolio)
        .filter(Holding.id == holding_id, Portfolio.user_id == user.id)
        .first_or_404()
    )
    portfolio = holding.portfolio

    if request.method == "POST":
        holding.symbol = request.form["symbol"].strip().upper()
        holding.quantity = float(request.form["quantity"])
        holding.avg_cost = float(request.form["avg_cost"])
        holding.total_cost = holding.quantity * holding.avg_cost

        first_buy_date_str = request.form.get("first_buy_date")
        if first_buy_date_str:
            holding.first_buy_date = datetime.strptime(first_buy_date_str, "%Y-%m-%d").date()
        else:
            holding.first_buy_date = None

        db.session.commit()
        flash("Holding updated.", "success")
        return redirect(url_for("portfolio_detail", portfolio_id=portfolio.id))

    return render_template(
        "holding_form.html", mode="edit", portfolio=portfolio, holding=holding
    )


@app.route("/holdings/<int:holding_id>/delete", methods=["POST"])
@login_required
def delete_holding(holding_id):
    user = current_user()
    holding = (
        Holding.query.join(Portfolio)
        .filter(Holding.id == holding_id, Portfolio.user_id == user.id)
        .first_or_404()
    )
    portfolio_id = holding.portfolio_id
    db.session.delete(holding)
    db.session.commit()
    flash("Holding deleted.", "info")
    return redirect(url_for("portfolio_detail", portfolio_id=portfolio_id))


@app.route("/holdings/<int:holding_id>/transactions/add", methods=["GET", "POST"])
@login_required
def add_transaction(holding_id):
    user = current_user()
    holding = (
        Holding.query.join(Portfolio)
        .filter(Holding.id == holding_id, Portfolio.user_id == user.id)
        .first_or_404()
    )
    portfolio = holding.portfolio

    if request.method == "POST":
        tx_type = request.form["tx_type"]
        quantity = float(request.form["quantity"])
        price = float(request.form["price"])
        tx_date_str = request.form.get("tx_date")
        fees_str = request.form.get("fees") or "0"

        tx_date = (
            datetime.strptime(tx_date_str, "%Y-%m-%d").date()
            if tx_date_str
            else date.today()
        )
        fees = float(fees_str)

        tx = Transaction(
            holding_id=holding.id,
            tx_type=tx_type,
            quantity=quantity,
            price=price,
            tx_date=tx_date,
            fees=fees,
        )
        db.session.add(tx)

        if tx_type == "BUY":
            new_total_cost = float(holding.total_cost or 0) + quantity * price + fees
            new_quantity = float(holding.quantity or 0) + quantity
            holding.quantity = new_quantity
            holding.avg_cost = new_total_cost / new_quantity if new_quantity > 0 else 0
            holding.total_cost = new_total_cost
            holding.last_buy_date = tx_date

        db.session.commit()
        flash("Transaction added.", "success")
        return redirect(url_for("portfolio_detail", portfolio_id=portfolio.id))

    return render_template("transaction_form.html", holding=holding)


@app.route("/portfolios/<int:portfolio_id>/refresh")
@login_required
def refresh_portfolio(portfolio_id):
    user = current_user()
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=user.id).first_or_404()

    for h in portfolio.holdings:
        ticker = yf.Ticker(h.symbol)
        info = ticker.info

        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
        market_cap = info.get("marketCap")

        h.current_price = float(current_price)
        h.market_cap = market_cap
        h.cap_category = classify_cap(market_cap)

        qty = float(h.quantity or 0)
        h.market_value = qty * float(current_price)
        h.unrealized_pl = float(h.market_value or 0) - float(h.total_cost or 0)

    db.session.commit()
    flash("Prices updated from yfinance.", "info")
    return redirect(url_for("portfolio_detail", portfolio_id=portfolio.id))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Connected to MySQL and ensured tables exist.")
    app.run(debug=True)
