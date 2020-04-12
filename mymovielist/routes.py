from flask import render_template, request, flash, redirect, url_for, jsonify
from run import app
import requests
import re
from mymovielist.forms import RegistrationForm, LoginForm, SearchForm
from mymovielist import db, bcrypt
from mymovielist.models import Users, Movies
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.useragents import UserAgent
from flask import session
from itertools import chain
import json
import aiohttp, aiofiles, asyncio

'''
TODO: ADD Filter on home page
DONE: Try to add async request with async file write
        still don't know that's the right way to do it or not.

'''

try:
    open('site.db')
except FileNotFoundError:
    db.create_all()
    db.session.commit()


def clear_html(show_summary):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', str(show_summary))


def myprevpage():
    page = request.args.get('page', default=1, type=int)
    if page <= 1:
        return url_for('home', page=1)
    return url_for('home', page=page - 1)


def mynextpage():
    page = request.args.get('page', default=1, type=int)
    if page >= session['page_no'] - 1:
        return url_for('home', page=session['page_no'] - 1)
    return url_for('home', page=page+1)


app.jinja_env.globals.update(clear_html=clear_html)
flag = 0
all_show = []


@app.route("/", methods=['GET', 'POST'])
@app.route("/home/<filter>", methods=['GET', 'POST'])
def home():
    global flag, all_show
    search_form = SearchForm()
    print(request.user_agent.platform)
    if search_form.validate_on_submit():
        show_name = search_form.search_ip.data
        return redirect(url_for('search_shows', show_name=show_name))
    page = request.args.get('page', default=1, type=int)
    if flag == 0:
        all_show = read_shows()
    shows = all_show[(page-1)*10: (page-1)*10+9]
    page_no = len(all_show) // 9 - 1
    session['page_no'] = page_no
    flag=True
    if request.user_agent.platform not in ['windows', 'macos', 'linux']:
        shows = all_show
        flag = False
    return render_template('home.html', title='home', shows=shows, page_no=page_no, func_prev=myprevpage,
                        func_next=mynextpage, search_form=search_form, flag=flag)


def read_shows():
    global flag
    print('read file')
    with open(r'mymovielist/static/shows.json', 'r') as fp:
        all_show = json.load(fp)
    flag = 1
    return all_show


@app.route("/about", methods=['GET'])
@login_required
def about():
    search_form = SearchForm()
    plan_to_watch_l = session['plan_to_watch']
    completed_l = session['completed']
    dropped_l = session['dropped']
    watching_l = session['watching']
    return render_template('about.html', search_form=search_form, plan_to_watch_l=plan_to_watch_l,
                            completed_l=completed_l, dropped_l=dropped_l, watching_l=watching_l)


@app.route("/search/<show_name>", methods=['GET', 'POST'])
def search_shows(show_name):
    search_form = SearchForm()
    if search_form.validate_on_submit():
        show_name = search_form.search_ip.data
        return redirect(url_for('search_shows', show_name=show_name))
    url = f"http://api.tvmaze.com/search/shows?"
    querystring = {"q": show_name}
    response = requests.request("GET", url, params=querystring)
    data_list = response.json()
    return render_template('search_show.html', title='Shows', data_list=data_list, search_form=search_form)


async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()


async def main(urls):
    tasks = []
    results = []
    async with aiohttp.ClientSession() as sess:
        for url in urls:
            tasks.append(fetch(sess, url))
        results = await asyncio.gather(*tasks)
    return results


@app.route("/search_id", methods=['GET', 'POST'])
@login_required
def search_show():
    search_form = SearchForm()
    if search_form.validate_on_submit():
        show_name = search_form.search_ip.data
        return redirect(url_for('search_shows', show_name=show_name))
    id_ = request.args.get('id_')
    url_1 = f"http://api.tvmaze.com/shows/{id_}"
    # data = requests.request("GET", url_1).json()

    url_2 = f"http://api.tvmaze.com/shows/{id_}/episodes" 
    # episodes = requests.request("GET", url_2).json()

    url_3 = f"http://api.tvmaze.com/shows/{id_}/cast"
    # cast = requests.request("GET", url_3).json()

    url_4 = f"http://api.tvmaze.com/shows/{id_}/seasons"
    # seasons = requests.request("GET", url_4).json()

    urls = [url_1, url_2, url_3, url_4]
    r = asyncio.run(main(urls))
    data = json.loads(r[0])
    episodes = json.loads(r[1])
    cast = json.loads(r[2])
    seasons = json.loads(r[3])

    sea_epi = {}
    for season in seasons:
        if season['number'] and season['episodeOrder']:
            se_no = int(season['number'])
            ep_no = int(season['episodeOrder'])
            sea_epi[se_no] = ep_no
    plan_to_watch_l = session['plan_to_watch']
    completed_l = session['completed']
    dropped_l = session['dropped']
    watching_l = [watch['movie_id'] for watch in session['watching']]
    return render_template('display_show.html', title=f'Show {data["name"]}', data=data, episodes=episodes, casts=cast,
                        sea_epi=sea_epi, search_form=search_form, plan_to_watch_l=plan_to_watch_l, completed_l=completed_l,
                        dropped_l=dropped_l, watching_l=watching_l)


@app.route("/plan_to_watch", methods=['GET'])
@login_required
def plan_to_watch():
    mes = ''
    movie_id = int(request.args.get('movie_id'))
    user_id = session["user_id"]
    l = session['plan_to_watch']
    s_w = [watch['movie_id'] for watch in session['watching']]
    if movie_id not in chain(session['completed'], session['dropped'], s_w):
        if not list(chain(session['completed'], session['dropped'], session['plan_to_watch'], session['watching'])):
            l.append(movie_id)
            m = Movies(plan_to_watch=l, user_id=user_id)
            db.session.add(m)
        else:
            l.append(movie_id)
            db.session.query(Movies).filter_by(user_id=user_id).update({Movies.plan_to_watch: l}, synchronize_session=False)
        db.session.commit()
        session['plan_to_watch'] = l
    else:
        mes = remove_and_add(movie_id, 'plan_to_watch', Movies.plan_to_watch)
    flash(f'{mes} Added to plan to watch list {session["plan_to_watch"]}', 'success')
    return redirect(url_for('search_show', id_=movie_id))


@app.route("/completed", methods=['GET'])
@login_required
def completed():
    mes = ''
    movie_id = int(request.args.get('movie_id'))
    user_id = session["user_id"]
    l = session['completed']
    s_w = [watch['movie_id'] for watch in session['watching']]
    if movie_id not in chain(session['plan_to_watch'], session['dropped'], s_w):
        if not list(chain(session['completed'], session['dropped'], session['plan_to_watch'], session['watching'])):
            l.append(movie_id)
            m = Movies(completed=l, user_id=user_id)
            db.session.add(m)
        else:
            l.append(movie_id)
            db.session.query(Movies).filter_by(user_id=user_id).update({Movies.completed: l}, synchronize_session=False)
        db.session.commit()
        session['completed'] = l
    else:
        mes = remove_and_add(movie_id, 'completed', Movies.completed)
    flash(f'{mes} Added to completed list {session["completed"]}', 'success')
    return redirect(url_for('search_show', id_=movie_id))


@app.route("/dropped", methods=['GET'])
@login_required
def dropped():
    mes = ''
    movie_id = int(request.args.get('movie_id'))
    user_id = session["user_id"]
    l = session['dropped']
    s_w = [watch['movie_id'] for watch in session['watching']]
    if movie_id not in chain(session['plan_to_watch'], session['completed'], s_w):
        if not list(chain(session['completed'], session['dropped'], session['plan_to_watch'], session['watching'])):
            l.append(movie_id)
            m = Movies(dropped=l, user_id=user_id)
            db.session.add(m)
        else:
            l.append(movie_id)
            db.session.query(Movies).filter_by(user_id=user_id).update({Movies.dropped: l}, synchronize_session=False)
        db.session.commit()
        session['dropped'] = l
    else:
        mes = remove_and_add(movie_id, 'dropped', Movies.dropped)
    flash(f'{mes} Added to dropped list {session["dropped"]}', 'success')
    return redirect(url_for('search_show', id_=movie_id))


@app.route("/watching", methods=['GET', 'POST'])
@login_required
def watching():
    mes = ''
    user_id = session["user_id"]
    l = session['watching']
    if request.method == "POST":
        data = {}
        data['movie_id'] = request.json['movie_id']
        data['se'] = request.json['se']
        data['ep'] = request.json['ep']
        s_w = [watch['movie_id'] for watch in session['watching']]
        if data['movie_id'] not in chain(session['completed'], session['dropped'], session['plan_to_watch']):
            if not list(chain(session['completed'], session['dropped'], session['plan_to_watch'], session['watching'])):
                l.append(data)
                m = Movies(watching=l, user_id=user_id)
                db.session.add(m)
            else:
                if data['movie_id'] in s_w:
                    for data_l in l:
                        if data_l['movie_id'] == data['movie_id']:
                            l.remove(data_l)
                            break
                l.append(data)
                db.session.query(Movies).filter_by(user_id=user_id).update({Movies.watching: l}, synchronize_session=False)
            db.session.commit()
            session['watching'] = l
            mes = f"Added to watching list {session['watching']}"
        else:
            mes = remove_and_add(data['movie_id'], 'watching', Movies.watching, data)
            mes = f"{mes} Added to watching list {session['watching']}"
        send_data = {'mes': mes}
        return jsonify(send_data)
    return redirect(url_for('search_show', id_=data['movie_id']))


def remove_and_add(movie_id, func_name, func, data=None):
    user_id = session["user_id"]

    if movie_id in session['completed']:
        old_l = session['completed']
        flag_name = 'completed'
        flag = Movies.completed
        old_l.remove(movie_id)
        l = session[func_name]
        if data:
            l.append(data)
        else:
            l.append(movie_id)
    elif movie_id in session['dropped']:
        old_l = session['dropped']
        flag_name = 'dropped'
        flag = Movies.dropped
        old_l.remove(movie_id)
        l = session[func_name]
        if data:
            l.append(data)
        else:
            l.append(movie_id)
    elif movie_id in session['plan_to_watch']:
        old_l = session['plan_to_watch']
        flag_name = 'plan_to_watch'
        flag = Movies.plan_to_watch
        old_l.remove(movie_id)
        l = session[func_name]
        if data:
            l.append(data)
        else:
            l.append(movie_id)
    else:
        old_l = session['watching']
        flag_name = 'watching'
        flag = Movies.watching
        for ol in old_l:
            if ol['movie_id'] == movie_id:
                key = ol
                break
        old_l.remove(key)
        l = session[func_name]
        l.append(movie_id)
    db.session.query(Movies).filter_by(user_id=user_id).update({func: l, flag: old_l}, synchronize_session=False)
    db.session.commit()
    session[flag_name] = old_l
    session[func_name] = l
    return f"Remove From {flag_name} and"


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    search_form = SearchForm()
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if search_form.validate_on_submit():
        show_name = search_form.search_ip.data
        return redirect(url_for('search_shows', show_name=show_name))
    if form.validate_on_submit():
        hased_password = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        username = form.username.data.strip()
        email = form.email.data.strip()
        user = Users(username=username, email=email, password=hased_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Your Account has been created!! You can login now', 'success')
    return render_template('register.html', title='register', form=form, search_form=search_form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    search_form = SearchForm()
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if search_form.validate_on_submit():
        show_name = search_form.search_ip.data
        return redirect(url_for('search_shows', show_name=show_name))
    if form.validate_on_submit():
        email_check = form.email.data
        password_check = form.password.data
        user = Users.query.filter_by(email=email_check).first()
        if user and bcrypt.check_password_hash(user.password, password_check):
            login_user(user, remember=form.remember.data)
            get_all_data_ready()
            next = request.args.get('next')
            if next:
                return redirect(next)
            return redirect(url_for('home'))
        else:
            flash('Provide Correct Detail Please!!!', 'danger')
    return render_template('login.html', title='login', form=form, search_form=search_form)


async def download_json(session, url):
    async with session.get(url, ssl=False) as res:

        async with aiofiles.open('mymovielist/static/shows.json', 'wb') as f:
            while True:
                chunk = await res.content.read(1024)
                if not chunk:
                    break
                await f.write(chunk)
            
        return await res.release()


async def main_json(url):
    async with aiohttp.ClientSession() as session:
        await download_json(session, url)


def get_all_data_ready():
    url = f"http://api.tvmaze.com/shows"
    '''response = requests.request("GET", url)
    all_show = response.json()
    with open(r'mymovielist/static/shows.json', 'w') as fp:
        json.dump(all_show, fp)'''
    asyncio.run(main_json(url))
    user_id = session["user_id"]
    print(user_id)
    movie = Movies.query.filter_by(user_id=user_id).first()
    if movie:
        session['plan_to_watch'] = movie.plan_to_watch if movie.plan_to_watch else []
        session['completed'] = movie.completed if movie.completed else []
        session['dropped'] = movie.dropped if movie.dropped else []
        session['watching'] = movie.watching if movie.watching else []
    else:
        session['plan_to_watch'] = []
        session['completed'] = []
        session['dropped'] = []
        session['watching'] = []


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))
