import hashlib
import hmac
import json
import math
import os
import re
import smtplib
import urllib
import uuid
from datetime import datetime

import utils
from urllib.request import urlopen, Request
from flask import Flask, render_template, request, url_for, redirect, session, jsonify, make_response
from flask_login import login_user, logout_user
from src import app, login
from src.admin import *
import requests


@app.context_processor
def repos():
    return {
        "cart": len(utils.total_room_by_receiptId(0))
    }


@app.route('/', methods=['post', 'get'])
def home_page():
    filter_room_list = []
    type_room_id = ""
    quantity_bed = ""
    price_sort = ""

    if request.method.__eq__('POST'):
        type_room_id = request.form.get('type-room-id')
        quantity_bed = request.form.get('quantity-bed')
        price_sort = request.form.get('price-sort')

    page = request.args.get('page', 1)
    filter_room_list = utils.filters_room(type_room_id=type_room_id,
                                          quantity_bed=quantity_bed,
                                          price_order_by=price_sort,
                                          page=int(page))

    page_counter = utils.count_rooms(type_room_id=type_room_id,
                                     quantity_bed=quantity_bed,
                                     price_order_by=price_sort)

    current_page = math.ceil(page_counter / app.config['PAGE_SIZE'])

    return render_template('index.html',
                           filter_room_list=filter_room_list,
                           pages=current_page,
                           type_room_id=type_room_id,
                           price_sort=price_sort)


@app.route('/about')
def about_us_page():
    return render_template('about-us.html')


def admin_stats_page():
    pass


@app.route('/register', methods=['post', 'get'])
def user_register():
    err_msg = ""
    if request.method.__eq__('POST'):
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        email = request.form.get('email')
        try:
            if password.strip().__eq__(confirm.strip()):

                utils.add_user(username=username,
                               password=password, email=email)
                return redirect(url_for('user_signin'))
            else:
                err_msg = "X??c nh???n m???t kh???u kh??ng tr??ng kh???p v???i M???t kh???u !!! "
        except Exception as ex:
            err_msg = "C?? l???i x???y ra r???i !! " + str(ex)

    return render_template('register.html', err_msg=err_msg)


@app.route('/user-login', methods=['post', 'get'])
def user_signin():
    err_msg = ''

    if request.method.__eq__('POST'):
        username = request.form.get('username')
        password = request.form.get('password')

        user = utils.check_login(username=username, password=password)
        if user:
            login_user(user=user)
            return redirect(url_for('home_page'))
        else:
            err_msg = 'Username hay password kh??ng ????ng, vui l??ng ki???m tra l???i'

    return render_template('login.html', err_msg=err_msg)


@app.route('/user-logout')
def user_signout():
    logout_user()
    return redirect(url_for('home_page'))


@login.user_loader
def user_load(user_id):
    return utils.get_user_by_id(user_id=user_id)



@app.route('/contact-page')
def contact_page():
    return render_template("contactPage.html")



@app.route('/my-room')
def cart():
    err = ""
    try:
        cart = utils.get_list_receipt_detail(0)
        total_money = utils.total_money(user_id=0)
    except:
        err = "Trang web l???i! Vui l??ng th??? l???i sau"
    return render_template('cart.html', list_cart=cart, total_money=total_money, err=err)


@app.route('/delete-cart', methods=['post'])
def delete_cart():
    data = json.loads(request.data)
    id = str(data.get("id"))
    tb = "???? x??a th??nh c??ng"
    try:
        utils.delete_Receipt_detail(id=id)
    except:
        tb = "L???i databasse! Vui l??ng th??? l???i sau!"

    # update cart

    return jsonify(tb, len(utils.total_room_by_receiptId(0)))


@app.route("/rooms/<int:room_id>")
def room_detail_page(room_id):
    room = utils.get_room_by_id(room_id)
    type_room = utils.get_type_room_by_room_id(room_id)
    return render_template('room-detail.html', room=room, type_room=type_room)


@app.route('/api/cart', methods=['post'])
def add_to_cart():
    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    data = json.loads(request.data)
    id = str(data.get("id"))
    name = data.get("name")
    price = data.get("price", 0)

    receive_day = data.get("receive-day")
    pay_day = data.get("pay-day")
    person_amount = str(data.get("person-amount"))

    cart = session.get('cart')

    if id in cart:
        cart[id]['quantity'] = cart[id]['quantity'] + 1
    else:
        cart[id] = {
            "id": id,
            "name": name,
            "price": price,
            "quantity": 1,
        }

    session['cart'] = cart

    booking_infor = {
        "receive_day": receive_day,
        "pay_day": pay_day,
        "person_amount": person_amount
    }

    quantity, price = utils.cart_stats(cart)
    utils.add_receipt_detail(room_id=int(id),
                             room_name=name,
                             price=float(price),
                             quantity=float(quantity),
                             receive_day=receive_day,
                             pay_day=pay_day,
                             person_amount=int(person_amount))
    print('person_amount', person_amount)

    return jsonify(utils.cart_stats(cart), cart, booking_infor, len(utils.total_room_by_receiptId(0)))


@app.route('/payment', methods=['post', 'get'])
def payment_page():
    list_booking_room = utils.get_list_receipt_detail(0)
    total_price = utils.total_money(user_id=0)

    # Default variable
    fullname = "default"
    email = "default"
    nation = "default"
    identify = "default"
    phone_number = "default"
    offline_payment = ""
    online_payment = ""
    is_sendmail_success = False

    # Validate variable
    fullname_validate = ""
    email_validate = ""
    nation_validate = ""
    identify_validate = ""
    phone_number_validate = ""

    # Open success modal
    is_open_modal = False

    if request.method.__eq__('POST'):
        fullname = request.form.get('payment-fullname')
        email = request.form.get('payment-email')
        nation = request.form.get('payment-nation')
        identify = request.form.get('payment-identify')
        phone_number = request.form.get('payment-phone-number')
        offline_payment = request.form.get('offline-payment')
        online_payment = request.form.get('online-payment')

    # print('online', online_payment)
    # print('ofline', offline_payment)

    # Validate fullname (th??m d??u c??ch v?? Ti???ng vi???t th?? check sai)
    if fullname == "":
        fullname_validate = "H??y nh???p h??? v?? t??n!"
    else:
        if re.match(r'[a-zA-Z\s]+$', fullname) is None:
            fullname_validate = "H??? t??n kh??ng h???p l???!"

    # Validate email
    if email == "":
        email_validate = "H??y nh???p email!"
    else:
        if re.match(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email) is None and email != "default":
            email_validate = "Email kh??ng h???p l???!"

    # Validate nation (th??m d??u c??ch v?? Ti???ng vi???t th?? check sai)
    if nation == "":
        nation_validate = "H??y nh???p t??n qu???c gia/khu v???c!"
    else:
        if re.match(r'[a-zA-Z\s]+$', nation) is None:
            nation_validate = "T??n qu???c gia/khu v???c kh??ng h???p l???!"

    # Validate identify
    if identify == "":
        identify_validate = "H??y nh???p s??? CMND/Passport!"
    else:
        if re.match('^[0-9]+$', identify) is None and email != "default":
            identify_validate = "S??? CMND/Passport kh??ng h???p l???!"

    # Validate phone number (not work)
    if phone_number == "":
        phone_number_validate = "H??y nh???p s??? ??i???n tho???i!"
    else:
        if re.match(r"[\d]{3}[\d]{3}[\d]{3}", phone_number) is None and email != "default":
            phone_number_validate = "S??? ??i???n tho???i kh??ng h???p l???!"

    # Check data before add to database
    if fullname != "default" and fullname != "" and fullname_validate == "" and \
            email != "default" and email != "" and email_validate == "" and \
            nation != "default" and nation != "" and nation_validate == "" and \
            identify != "default" and identify != "" and identify_validate == "" and \
            phone_number != "default" and phone_number != "" and phone_number_validate == "":
        utils.add_rental_voucher_detail(visit_name=fullname,
                                        type_visit_id=1,
                                        phone_number=phone_number,
                                        rental_voucher_id=1,
                                        email=email,
                                        visit_name_id=1,
                                        nation=nation)
        utils.add_rental_voucher(booking_date=datetime.now())

        rental_voucher_detail_id = utils.get_new_record_rental_voucher_detai()[0]
        print('check rental voucher id', rental_voucher_detail_id)
        message = 'X??C NH???N ?????T PH??NG TH??NH C??NG\n\nCh??ng t??i xin tr??n tr???ng g???i ?????n qu?? kh??ch th?? x??c nh???n r???ng qu?? kh??ch ???? th???c hi???n thao t??c ?????t ph??ng th??nh c??ng.\nC???m ??n qu?? kh??ch ???? s??? d???ng dich v??? c???a Lotus Hotel.\nM?? ?????t ph??ng c???a qu?? kh??ch l??: ' + str(rental_voucher_detail_id) + ' \n????? nh???n ph??ng, qu?? kh??ch vui l??ng tr??nh di???n m?? ?????t ph??ng cho l??? t??n t???i s???nh ch??nh kh??ch s???n.\nXin tr??n tr???ng c???m ??n.\n\n\nLI??N H???\nEmail: hotel.lotus371@gmail.com\nT???ng ????i: 1-548-854-8898\n?????a ch???: 371 Nguy???n Ki???m, qu???n G?? V???p, TP. H??? Ch?? Minh'

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("hotel.lotus371@gmail.com", "!Hotellotus371")
        server.sendmail("hotel.lotus371@gmail.com", email, message.encode('utf-8'))
        server.quit()
        try:
            print('check mail sending', server.sendmail("hotel.lotus371@gmail.com", email, message.encode('utf-8')))
        except (IOError, OSError):
            print("Handling OSError...")
        is_sendmail_success = True

        # Check modal will be open
        if fullname != "default" and fullname_validate == "" and \
                email != "default" and email_validate == "" and \
                nation != "default" and nation_validate == "" and \
                identify != "default" and identify_validate == "" and \
                phone_number != "default" and phone_number_validate == "" and \
                is_sendmail_success is True:
            is_open_modal = True

    return render_template('payment.html',
                           list_booking_room=list_booking_room,
                           total_price=total_price,
                           fullname_validate=fullname_validate,
                           email_validate=email_validate,
                           nation_validate=nation_validate,
                           identify_validate=identify_validate,
                           phone_number_validate=phone_number_validate,
                           is_open_modal=is_open_modal,
                           is_sendmail_success=is_sendmail_success)


@app.route('/payment/success')
def payment_success_page():
    # Delete all receipt detail when payment success
    utils.delete_all_receipt_detail()
    return render_template("payment-success.html")


if __name__ == "__main__":
    from src.admin import *

    app.run(debug=True)
