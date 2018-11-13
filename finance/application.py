import os
import datetime

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Get user_id from session
    userid = session["user_id"]

    # Query database from users table for username and declare variable to hold username
    rows = db.execute("SELECT * FROM users WHERE id = :id", id=userid)
    user_name = rows[0]["username"]
    # Query data from "portfolio" table
    portfolio_list = db.execute("SELECT username, symbol, SUM(shares) AS total_shares, price\
                        FROM history GROUP BY username, symbol HAVING username = :username",
                        username=user_name)

    # Iterate over each dict_item in portfolio_list
    # Select "symbol" for key and use lookup() to get stock_name
    # Add stock_name and total_value to dict_item in portfolio_list
    for dict_item in portfolio_list[:]:
        for key, value in dict_item.items():
                symbol = dict_item.get("symbol")
                name = lookup(symbol)
                name = name.get("name")
                total_value = usd(dict_item.get("total_shares") * dict_item.get("price"))
        dict_item.update({"stock_name": name, "total_value": total_value})

    return render_template("index.html", portfolio_list=portfolio_list, cash=rows[0]["cash"])


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # User reached route via GET (as by clicking a link or via redirect)
    # Render buy.html for user to input "symbol" and "shares"
    if request.method == "GET":
        return render_template("buy.html")

    else:
        # Use lookup() in helpers.py to look up stock price using symbol
        # Declare variable to hold "price" and "symbol" for later use
        quote_dict = lookup(request.form.get("symbol"))
        stock_price = quote_dict["price"]
        stock_symbol = quote_dict["symbol"]

        # Declare variable to hold number of shares passed by user
        total_shares = int(request.form.get("shares"))

        # Get user_id from session
        userid = session["user_id"]

        # Check for invalid symbol and return apology
        if not quote_dict:
            return apology("incorrect symbol", 403)
            return redirect("/buy")
        # If symbol is valid, check if user has enough money in the account
        else:
            # Query database from users table for cash and declare variable to hold cash and username
            rows = db.execute("SELECT * FROM users WHERE id = :id", id=userid)
            user_cash = rows[0]["cash"]
            user_name = rows[0]["username"]

            # If user has enough cash, INSERT  new data into the "transaction" table and UPDATE "cash" in the "users" table
            if user_cash >= stock_price * total_shares:
                db.execute("INSERT INTO history (username, symbol, shares, price, date, cost) VALUES(:name, :symbol, :shares, :price, :date, :cost)",
                            name=user_name,
                            symbol=stock_symbol,
                            shares=total_shares,
                            price=stock_price,
                            date=datetime.datetime.now(),
                            cost=stock_price * total_shares)

                # Update the "symbol", "shares", "price", "total_value", "cash" in the "users" table
                user_cash -= total_shares * stock_price
                db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash=user_cash, id=userid)

        return render_template("bought.html", symbol=stock_symbol,
                                        name=user_name,
                                        shares=total_shares,
                                        price=stock_price,
                                        total=stock_price * total_shares,
                                        cash=usd(user_cash))


# @app.route("/history")
# @login_required
# def history():
#     """Show history of transactions"""
#     return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to register page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


# @app.route("/logout")
# def logout():
#     """Log user out"""

#     # Forget any user_id
#     session.clear()

#     # Redirect user to login form
#     return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # User reached route via GET (as by clicking a link or via redirect)
    if request.method == "GET":
        return render_template("quote.html")

    else:
        # Check for valid symbol and render quoted.html to display stock price
        # Otherwise, return apology
        quote_dict = lookup(request.form.get("quote"))
        if not quote_dict:
            return apology("incorrect symbol", 403)
            return redirect("/quote")
        else:
            return render_template("quoted.html", name=quote_dict["name"], symbol=quote_dict["symbol"], price=quote_dict["price"])

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via GET (as by clicking a link or via redirect)
    if request.method == "GET":
        return render_template("register.html")

    else:
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure password is confirmed and matched
        elif not request.form.get("pw_confirm"):
            return apology("must confirm password", 403)
        elif request.form.get("password") != request.form.get("pw_confirm"):
            return apology("password doesn't match", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # Add username to database if username does not already exist.
        # Otherwise, return apology
        if not rows:
            db.execute("INSERT INTO users (username, hash) VALUES(:name, :password)", name=request.form.get("username"), password=generate_password_hash(request.form.get("password")))
            return redirect("/")
        else:
            return apology("username already exists", 403)
            return redirect("/register")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == 'GET':
        return render_template("sell.html")


# def errorhandler(e):
#     """Handle error"""
#     return apology(e.name, e.code)


# # listen for errors
# for code in default_exceptions:
#     app.errorhandler(code)(errorhandler)
