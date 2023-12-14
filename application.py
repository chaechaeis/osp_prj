import json
import os
from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify
from database import DBhandler
import hashlib
import sys
import firebase_admin
from firebase_admin import credentials, db
from werkzeug.utils import secure_filename
import math

application = Flask(__name__, template_folder="templates", static_folder="static")
application.config["SECRET_KEY"] = "helloosp"

DB = DBhandler()


# Firebase Admin SDK 초기화
cred = credentials.Certificate("authentication/ewha-market-6d9f4-firebase-adminsdk-g6fth-76b5b461d8.json")  # 자신의 서비스 계정 키 경로로 설정
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://ewha-market-6d9f4-default-rtdb.firebaseio.com/'  # Firebase 프로젝트의 데이터베이스 URL로 설정
})


@application.route("/")
def hello():
    # return render_template("index.html")
    return redirect(url_for('view_list'))


@application.route("/reg_items")
def reg_items():
    return render_template("reg_items.html")


@application.route("/list")
def view_list():
    page = request.args.get("page", 0, type=int)
    category = request.args.get("category", "all")
    per_page = 6  # item count to display per page
    per_row = 3  # item count to display per row
    row_count = int(per_page / per_row)
    start_idx = per_page * page
    end_idx = per_page * (page + 1)
    if category=="all":
        data = DB.get_items() #read the table
    else:
        data = DB.get_items_bycategory(category)
    if data is None or not data:
        data = {}
    data = dict(sorted(data.items(), key=lambda x: x[0], reverse=False))
    item_counts = len(data)
    if item_counts<=per_page:
        data = dict(list(data.items())[:item_counts])
    else:
        data = dict(list(data.items())[start_idx:end_idx])
    tot_count = len(data)
    for i in range(row_count):  # last row
        if (i == row_count - 1) and (tot_count % per_row != 0):
            locals()['data_{}'.format(i)] = dict(list(data.items())[i * per_row:])
        else:
            locals()['data_{}'.format(i)] = dict(list(data.items())[i * per_row:(i + 1) * per_row])
    return render_template("list.html", datas=data.items(), row1=locals()['data_0'].items(),
                           row2=locals()['data_1'].items(), limit=per_page,
                           page=page, page_count=int(math.ceil(item_counts/per_page)),
                           total=item_counts, category=category)


@application.route("/review")
def view_review():
    page = request.args.get("page", 0, type=int)
    per_page=6 # item count to display per page
    per_row=3# item count to display per row
    row_count=int(per_page/per_row)
    start_idx=per_page*page
    end_idx=per_page*(page+1)
    data = DB.get_reviews()
    if data is not None:
        item_counts = len(data)
        data = dict(list(data.items())[start_idx:end_idx])
        tot_count = len(data)
    else:
        # Handle the case where data is None, for example, set default values or raise an exception
        item_counts = 0
        data = {}
        tot_count = 0
    for i in range(row_count):#last row
        if (i == row_count-1) and (tot_count%per_row != 0):
            locals()['data_{}'.format(i)] = dict(list(data.items())[i*per_row:])
        else:
            locals()['data_{}'.format(i)] = dict(list(data.items())[i*per_row:(i+1)*per_row])
    return render_template("review.html", datas=data.items(), row1=locals()['data_0'].items(), row2=locals()['data_1'].items(),
                           limit=per_page, page=page, page_count=int((item_counts/per_page)+1), total=item_counts)


@application.route("/view_review_detail/<name>/")
def view_review_detail(name):
    review_data = DB.get_review_byname(name)
    return render_template("review_detail.html", review_data=review_data)


@application.route("/reg_reviews")
def reg_reviews():
    return render_template("reg_reviews.html")


@application.route("/submit_item_post", methods=['POST'])
def reg_item_submit_post():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    image_files = request.files.getlist("file")
    
    if not image_files or all(file.filename == '' for file in image_files):
        flash('No selected file')
        return redirect(request.url)
    
    img_paths = [] # 이미지 url을 저장할 리스트 생성
    
    for file in image_files:
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join("static/images", filename))
            img_url = url_for('static', filename=f'images/{filename}')
            img_paths.append(img_url)
            
    data = request.form
    seller_id =session.get('id','')
    DB.insert_item(data['name'], data, img_paths, seller_id)
    return render_template("submit_item_result.html", data=data, img_paths=img_paths)
    
    

@application.route("/login")
def login():
    return render_template("login.html")


@application.route("/login_confirm", methods=['POST'])
def login_user():
    id_ = request.form['id']
    pw = request.form['pw']
    pw_hash = hashlib.sha256(pw.encode('utf-8')).hexdigest()
    if DB.find_user(id_, pw_hash):
        session['id'] = id_
        return redirect(url_for('view_list'))
    else:
        flash("Wrong ID or PW!")
        return render_template("login.html")


@application.route("/signup")
def signup():
    return render_template("signup.html")


@application.route("/signup_post", methods=['POST'])
def register_user():
    data = request.form
    pw = request.form['pw']
    pw_hash = hashlib.sha256(pw.encode('utf-8')).hexdigest()
    if DB.insert_user(data, pw_hash):
        return render_template("login.html")
    else:
        flash("user id already exists!")
        return render_template("signup.html")


@application.route("/logout")
def logout_user():
    session.clear()
    return redirect(url_for('view_list'))


@application.route("/dynamicurl/<varible_name>/")
def DynamicUrl(varible_name):
    return str(varible_name)


@application.route("/view_detail/<name>/")
def view_item_detail(name):
    data = DB.get_item_byname(str(name))
    return render_template("detail.html", name=name, data=data)


@application.route("/search", methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        try:
            keyword = request.form['keyword']  # 폼 필드 이름을 'keyword'로 수정
            # DBhandler 클래스의 인스턴스를 생성
            db_handler = DB  # 괄호를 추가하지 않습니다.
            results = db_handler.search_items(keyword)  # 검색 결과를 가져옴

            # 검색 결과를 search_result.html로 렌더링
            return render_template("search_result.html", results=results)
        except KeyError:
            flash("Missing 'keyword' in the request.")
            return render_template("search.html")

    return render_template("search.html")


@application.route("/search_result", methods=['GET'])
def search_result():
    search_query = request.args.get("search")  # 검색어를 쿼리 파라미터로 받아옴

    # DB에서 검색 결과를 가져오는 로직 (DBhandler 클래스의 search_items 메서드 활용)
    results = DB.search_items(search_query)  # 검색 결과를 리스트로 받아옴

    # 검색 결과를 JSON 형식으로 반환
    return jsonify(results)


# Flask 애플리케이션 코드
@application.route("/view_item_details/<name>/")
def view_item_details(name):
    # DBhandler 클래스의 get_item_byname 메서드를 사용하여 해당 상품의 정보를 가져옵니다.
    data = DB.get_item_byname(name)

    if data:
        return render_template("detail.html", name=name, data=data)
    else:
        # 해당 상품이 존재하지 않을 경우 처리 (예: 에러 페이지 또는 다른 처리)
        return render_template("error.html", message="해당 상품을 찾을 수 없습니다.")


@application.route("/reg_review_init/<name>/")
def reg_review_init(name):
    return render_template("reg_reviews.html", name=name)


@application.route("/reg_review", methods=['POST'])
def reg_review():
    if 'id' in session:
        user_id = session['id']
        data = request.form
        DB.reg_review(data, user_id, img_path)  # user_id를 추가하여 메서드 호출
        return redirect(url_for('view_review', name=data['name']))
    else:
        flash('로그인이 필요합니다.')
        return redirect(url_for('login'))


@application.route('/show_heart/<name>/', methods=['GET'])
def show_heart(name):
    if 'id' in session:
        my_heart = DB.get_heart_byname(session['id'], name)
        return jsonify({'my_heart': my_heart})
    else:
        # 사용자가 로그인되지 않은 경우에 대한 처리
        return jsonify({'error': '로그인이 필요합니다'})


@application.route('/like/<name>/', methods=['POST'])
def like(name):
    my_heart = DB.update_heart(session['id'],'Y',name)
    return jsonify({'msg': '좋아요 완료!'})


@application.route('/unlike/<name>/', methods=['POST'])
def unlike(name):
    my_heart = DB.update_heart(session['id'],'N',name)
    return jsonify({'msg': '안좋아요 완료!'})


@application.route("/submit_review_post", methods=['POST'])
def submit_review_post():
    image_file = request.files["file"]
    image_file.save("static/images/{}".format(image_file.filename))
    data = request.form
    user_id = session['id']
    
    # 상품 이름을 가져오기
    product_name = data.get('name')
    
    # 데이터베이스에서 판매자 ID 조회
    db_handler = DBhandler()
    product_info = db_handler.get_item_byname(product_name)
    seller_id = product_info.get("seller", "")  # 판매자 ID 가져오기
    
    DB.reg_review(data, image_file.filename, user_id, seller_id)
    
    return render_template("submit_review_result.html", data=data,
                           img_path="static/images/{}".format(image_file.filename))


@application.route('/mypage')
def mypage():
    if 'id' in session:
        user_id = session['id']

        # 좋아요한 상품 정보를 가져옴
        likes = DB.get_likes(user_id)[:3]  # 최근 등록한 3개만 선택

        # 사용자가 작성한 리뷰 정보를 가져옴
        user_reviews = DB.get_user_reviews(user_id)[:3]  # 최근 등록한 3개만 선택

        # 사용자가 등록한 상품 정보를 가져옴
        user_items = DB.get_user_items(user_id)[:3]  # 최근 등록한 3개만 선택

        return render_template('mypage.html', likes=likes, user_reviews=user_reviews, user_items=user_items)
    else:
        flash('로그인이 필요합니다.')
        return redirect(url_for('login'))  # 로그인하지 않은 경우 로그인 페이지로 리다이렉트


# 사용자가 좋아요한 상품을 가져오는 라우트 함수
@application.route('/my_likes')
def my_likes():
    if 'id' in session:
        user_id = session['id']
        likes = DB.get_likes(user_id)  # 좋아요한 상품 정보를 딕셔너리로 가져옴
        page_count = (len(likes) + 5) // 6
        return render_template('my_likes.html', likes=likes, page_count=page_count)
    else:
        # 사용자가 로그인되지 않은 경우에 대한 처리
        flash('로그인이 필요합니다.')
        return redirect(url_for('login'))  # 로그인 페이지로 리다이렉트


@application.route("/sales_history")
def sales_history():
    if 'id' in session:
        user_id = session['id']
        
        # 사용자가 등록한 상품 수를 얻어오는 메서드 (예: DB에서 가져온다고 가정)
        user_items_count = DB.get_user_items_count(user_id)  # 사용자가 등록한 상품 수
        
        per_page = 6  # 페이지당 항목 수 (원하는 값으로 설정)
        page_count = (user_items_count + per_page - 1) // per_page  # 페이지 수 계산
        
        user_items = DB.get_user_items(user_id)  # 실제로 사용자가 등록한 상품을 가져오는 메서드로 변경
        return render_template("sales_history.html", user_items=user_items, page_count=page_count)
    else:
        flash('로그인이 필요합니다.')
        return redirect(url_for('login'))  # 로그인하지 않은 경우 로그인 페이지로 리다이렉트


@application.route("/my_review")
def my_review():
    if 'id' in session:
        user_id = session['id']
        user_reviews = DB.get_user_reviews(user_id)  # 실제로 사용자가 등록한 상품을 가져오는 메서드로 변경
        user_reviews_count = DB.get_user_reviews_count(user_id)
        per_page = 6  # 페이지당 항목 수 (원하는 값으로 설정)
        page_count = (user_reviews_count + per_page - 1) // per_page  # 페이지 수 계산
        return render_template("my_review.html", user_reviews=user_reviews, page_count=page_count)
    else:
        flash('로그인이 필요합니다.')
        return redirect(url_for('login'))  # 로그인하지 않은 경우 로그인 페이지로 리다이렉트


@application.route("/faq")
def faq():
    return render_template("faq.html")


if __name__ == "__main__":
    application.run(host='0.0.0.0', debug=True)
