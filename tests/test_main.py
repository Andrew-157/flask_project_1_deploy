import pytest
from flask import Response
from werkzeug.security import generate_password_hash
from .conftest import AuthActions
from app import db
from app.models import User, Question, QuestionVote, QuestionViews, Answer, AnswerVote


def test_index(client, auth: AuthActions):
    response: Response = client.get('/')
    assert response.status_code == 200
    assert b'Register' in response.data
    assert b'Login' in response.data

    auth.login()
    response: Response = client.get('/')
    assert response.status_code == 200
    assert b'Logout' in response.data
    assert b'Change profile' in response.data


def test_post_question(client, auth: AuthActions, app):
    auth.login()
    assert client.get('/questions/ask/').status_code == 200
    response: Response = client.post('/questions/ask/',
                                     data={'title': 'How to iterate through Python List?',
                                           'details': 'I am only starting to learn Python,\
                                do not know how to iterate through list',
                                           'tags': 'python, iteration, programming'})
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers['Location'] == '/'
    assert messages['success'] == 'You successfully asked new question!'
    with app.app_context():
        test_user = db.session.query(User).filter_by(
            username='test_user').first()
        question = db.session.query(Question).filter(
            (Question.user_id == test_user.id) &
            (Question.title == 'How to iterate through Python List?')
        ).first()
        assert question is not None


@pytest.mark.parametrize(('title', 'message'),
                         (
    ('', b'Title is required to post a question.'),
    ('dfrg',  b'Title is too short.')
))
def test_post_question_validate_input(client, auth: AuthActions, title, message):
    auth.login()
    response: Response = client.post('/questions/ask/',
                                     data={'title': title,
                                           'details': '',
                                           'tags': ''})
    assert response.status_code == 200
    assert message in response.data


def test_post_question_for_not_logged_user(client):
    response = client.get('/questions/ask/')
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers['Location'] == '/'
    assert messages['info'] == 'You need to be authenticated to ask a question.'


def test_update_question_for_question_owner(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        db.session.add(question)
        db.session.commit()
        db.session.refresh(question)

    auth.login()
    assert client.get(f'/questions/{question.id}/update/').status_code == 200
    response = client.post(f'/questions/{question.id}/update/',
                           data={'title': 'How to create index for a row in MySQL?',
                                 'details': '',
                                 'tags': ''})
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers['Location'] == f'/questions/{question.id}/'
    assert messages['success'] == 'You successfully updated your question.'
    with app.app_context():
        question = db.session.query(Question).\
            filter_by(title='How to create index for a row in MySQL?').first()
        assert question != None
        assert question.updated != None


@pytest.mark.parametrize(('title', 'message'),
                         (
    ('', b'Title is required.'),
    ('dfrg', b'Title is too short.')
))
def test_update_question_validate_input_for_question_owner(app, client, auth: AuthActions, title, message):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        db.session.add(question)
        db.session.commit()
        db.session.refresh(question)

    auth.login()
    assert client.get(f'/questions/{question.id}/update/').status_code == 200
    response = client.post(f'/questions/{question.id}/update/',
                           data={'title': title,
                                 'details': '',
                                 'tags': ''})
    assert response.status_code == 200
    assert message in response.data


def test_update_question_by_user_that_does_not_own_question(app, client, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        new_user = User(username='some_user',
                        email='some_user@gmail.com',
                        password=generate_password_hash('34somepassword34'))
        db.session.add(question)
        db.session.add(new_user)
        db.session.commit()
        db.session.refresh(question)

    auth.login(email='some_user@gmail.com', password='34somepassword34')
    assert client.get(f'/questions/{question.id}/update/').status_code == 403


def test_update_question_for_not_logged_user(client, app):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        db.session.add(question)
        db.session.commit()
        db.session.refresh(question)

    response = client.get(f'/questions/{question.id}/update/')
    assert response.status_code == 302
    assert (response.headers["Location"].startswith('/auth/login/'))


def test_update_nonexistent_question_for_logged_user(client, app, auth: AuthActions):
    auth.login()
    response = client.get('/questions/7890/update/')
    assert response.status_code == 404


def test_question_detail(app, client):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        db.session.add(question)
        db.session.commit()
        db.session.refresh(question)

    response = client.get(f'/questions/{question.id}/')
    assert response.status_code == 200
    assert str(question.title).encode("utf-8") in response.data


def test_question_detail_for_logged_user(app, client, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        db.session.add(question)
        db.session.commit()
        db.session.refresh(question)
        db.session.refresh(test_user)
    auth.login()
    response = client.get(f'/questions/{question.id}/')
    assert response.status_code == 200
    assert str(question.title).encode("utf-8") in response.data
    with app.app_context():
        view = db.session.query(QuestionViews).filter(
            (QuestionViews.user_id == test_user.id) &
            (QuestionViews.question_id == question.id)
        ).first()
        assert view is not None


def test_question_detail_for_question_owner(app, client, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        db.session.add(question)
        db.session.commit()
        db.session.refresh(question)
    auth.login()
    response = client.get(f'/questions/{question.id}/')
    assert response.status_code == 200
    assert b'Update your question' in response.data
    assert b'Delete your question' in response.data


def test_question_detail_for_nonexistent_question(app, client, auth: AuthActions):
    response = client.get('/questions/6789/')
    assert response.status_code == 404


def test_delete_question_for_question_owner(app, client, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        db.session.add(question)
        db.session.commit()
        db.session.refresh(question)
    auth.login()
    response = client.post(f'/questions/{question.id}/delete/')
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers["Location"] == '/'
    assert messages["success"] == 'You successfully deleted your question.'
    with app.app_context():
        question = db.session.query(Question).filter_by(
            title='How to iterate through Python List?'
        ).first()
        assert question is None


def test_delete_nonexistent_question_by_logged_user(client, auth: AuthActions):
    auth.login()
    response = client.post('/questions/4567/delete/')
    assert response.status_code == 404


def test_delete_question_for_not_logged_user(client):
    response = client.post('/questions/4567/delete/')
    assert response.status_code == 302
    assert (response.headers["Location"].startswith('/auth/login/'))


def test_delete_question_for_logged_user_that_does_not_own_question(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        new_user = User(username='some_user',
                        email='some_user@gmail.com',
                        password=generate_password_hash('34somepassword34'))
        db.session.add(question)
        db.session.add(new_user)
        db.session.commit()
        db.session.refresh(question)
    auth.login(email='some_user@gmail.com', password='34somepassword34')
    response = client.post(f'/questions/{question.id}/delete/')
    assert response.status_code == 403


def test_upvote_question_for_logged_user_without_vote(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        db.session.add(question)
        db.session.commit()
        db.session.refresh(question)
        db.session.refresh(test_user)

    auth.login()
    response = client.post(f'/questions/{question.id}/upvote/')
    assert response.status_code == 302
    assert response.headers["Location"] == f"/questions/{question.id}/"
    with app.app_context():
        upvote = db.session.query(QuestionVote).filter(
            (QuestionVote.question_id == question.id) &
            (Question.user_id == test_user.id) &
            (QuestionVote.is_upvote == True)
        ).first()
        assert upvote is not None


def test_upvote_question_for_logged_user_with_upvote(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        question_upvote = QuestionVote(question=question, user=test_user,
                                       is_upvote=True)
        db.session.add(question_upvote)
        db.session.commit()
        db.session.refresh(question)
        db.session.refresh(test_user)

    auth.login()
    response = client.post(f'/questions/{question.id}/upvote/')
    assert response.status_code == 302
    assert response.headers["Location"] == f"/questions/{question.id}/"
    with app.app_context():
        upvote = db.session.query(QuestionVote).filter(
            (QuestionVote.question_id == question.id) &
            (Question.user_id == test_user.id) &
            (QuestionVote.is_upvote == True)
        ).first()
        assert upvote is None


def test_upvote_question_for_logged_user_with_downvote(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        question_downvote = QuestionVote(question=question, user=test_user,
                                         is_upvote=False)
        db.session.add(question_downvote)
        db.session.commit()
        db.session.refresh(question)
        db.session.refresh(test_user)

    auth.login()
    response = client.post(f'/questions/{question.id}/upvote/')
    assert response.status_code == 302
    assert response.headers["Location"] == f"/questions/{question.id}/"
    with app.app_context():
        upvote = db.session.query(QuestionVote).filter(
            (QuestionVote.question_id == question.id) &
            (Question.user_id == test_user.id) &
            (QuestionVote.is_upvote == True)
        ).first()
        assert upvote is not None


def test_upvote_question_for_not_logged_user(client, app):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        db.session.add(question)
        db.session.commit()
        db.session.refresh(question)
    response = client.post(f'/questions/{question.id}/upvote/')
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers["Location"] == f"/questions/{question.id}/"
    assert messages['info'] == 'You have to authenticate to vote for a question'


def test_upvote_question_for_logged_user_for_nonexistent_question(client, app, auth: AuthActions):
    auth.login()
    response = client.post('/questions/7890/upvote/')
    assert response.status_code == 404


def test_downvote_question_for_logged_user_without_vote(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        db.session.add(question)
        db.session.commit()
        db.session.refresh(question)
        db.session.refresh(test_user)

    auth.login()
    response = client.post(f'/questions/{question.id}/downvote/')
    assert response.status_code == 302
    assert response.headers["Location"] == f"/questions/{question.id}/"
    with app.app_context():
        downvote = db.session.query(QuestionVote).filter(
            (QuestionVote.question_id == question.id) &
            (Question.user_id == test_user.id) &
            (QuestionVote.is_upvote == False)
        ).first()
        assert downvote is not None


def test_downvote_question_for_logged_user_with_downvote(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        question_downvote = QuestionVote(question=question, user=test_user,
                                         is_upvote=False)
        db.session.add(question_downvote)
        db.session.commit()
        db.session.refresh(question)
        db.session.refresh(test_user)

    auth.login()
    response = client.post(f'/questions/{question.id}/downvote/')
    assert response.status_code == 302
    assert response.headers["Location"] == f"/questions/{question.id}/"
    with app.app_context():
        downvote = db.session.query(QuestionVote).filter(
            (QuestionVote.question_id == question.id) &
            (Question.user_id == test_user.id) &
            (QuestionVote.is_upvote == False)
        ).first()
        assert downvote is None


def test_downvote_question_for_logged_user_with_upvote(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        question_upvote = QuestionVote(question=question, user=test_user,
                                       is_upvote=True)
        db.session.add(question_upvote)
        db.session.commit()
        db.session.refresh(question)
        db.session.refresh(test_user)

    auth.login()
    response = client.post(f'/questions/{question.id}/downvote/')
    assert response.status_code == 302
    assert response.headers["Location"] == f"/questions/{question.id}/"
    with app.app_context():
        downvote = db.session.query(QuestionVote).filter(
            (QuestionVote.question_id == question.id) &
            (Question.user_id == test_user.id) &
            (QuestionVote.is_upvote == False)
        ).first()
        assert downvote is not None


def test_downvote_question_for_not_logged_user(client, app):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        db.session.add(question)
        db.session.commit()
        db.session.refresh(question)
    response = client.post(f'/questions/{question.id}/downvote/')
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers["Location"] == f"/questions/{question.id}/"
    assert messages['info'] == 'You have to authenticate to vote for a question'


def test_downvote_question_for_logged_user_for_nonexistent_question(client, app, auth: AuthActions):
    auth.login()
    response = client.post('/questions/7890/downvote/')
    assert response.status_code == 404


def test_questions_by_tag(client):
    response = client.get('/tags/some_tag/')
    assert response.status_code == 200


def test_post_answer_for_logged_user(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        db.session.add(question)
        db.session.commit()
        db.session.refresh(question)
        db.session.refresh(test_user)

    auth.login()
    response = client.get(f'/questions/{question.id}/answer/')
    assert response.status_code == 200
    assert str(question.title).encode("utf-8") in response.data
    response = client.post(f'/questions/{question.id}/answer/',
                           data={'content': "This is my answer to your question."})
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers["Location"] == f"/questions/{question.id}/"
    assert messages["success"] == 'You successfully published your answer.'
    with app.app_context():
        answer = db.session.query(Answer).filter(
            (Answer.question_id == question.id) &
            (Answer.user_id == test_user.id)
        ).first()
        assert answer is not None


@pytest.mark.parametrize(('content', 'message'),
                         (
    ('', b'To publish an answer, you need to provide content for it.'),
    ('short', b'Content of your answer is too short.')
))
def test_post_answer_validate_input(client, app, auth: AuthActions, content, message):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        db.session.add(question)
        db.session.commit()
        db.session.refresh(question)

    auth.login()
    response = client.post(f'/questions/{question.id}/answer/',
                           data={'content': content})
    assert response.status_code == 200
    assert message in response.data


def test_post_answer_for_not_logged_user(client, app):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        db.session.add(question)
        db.session.commit()
        db.session.refresh(question)
    response = client.get(f'/questions/{question.id}/answer/')
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers["Location"] == f'/questions/{question.id}/'
    assert messages['info'] == 'To leave an answer for a question, become an authenticated user.'


def test_post_answer_for_nonexistent_question(client):
    response = client.get("/questions/67890/answer/")
    assert response.status_code == 404


def test_update_answer_by_logged_user_that_owns_answer(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        answer = Answer(user=test_user,
                        question=question, content="My answer to your question.")
        db.session.add(answer)
        db.session.commit()
        db.session.refresh(answer.question)
        db.session.refresh(test_user)

    auth.login()
    response = client.get(f"/answers/{answer.id}/update/")
    assert response.status_code == 200
    assert str(answer.question.title).encode("utf-8") in response.data
    response = client.post(f"/answers/{answer.id}/update/",
                           data={'content': 'My updated answer for your question.'})
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers["Location"] == f"/questions/{question.id}/"
    assert messages['success'] == 'You successfully updated your answer.'
    with app.app_context():
        answer = db.session.query(Answer).filter(
            (Answer.question_id == question.id) &
            (Answer.user_id == test_user.id)
        ).first()
        assert answer.updated is not None


@pytest.mark.parametrize(('content', 'message'),
                         (
    ('', b'You cannot update your answer without content.'),
    ('short', b'Content of your answer is too short.')
))
def test_update_answer_by_logged_user_that_owns_answer_validate_input(client,
                                                                      app,
                                                                      auth: AuthActions,
                                                                      content,
                                                                      message):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        answer = Answer(user=test_user,
                        question=question, content="My answer to your question.")
        db.session.add(answer)
        db.session.commit()
        db.session.refresh(answer)
        db.session.refresh(test_user)

    auth.login()
    response = client.post(f"/answers/{answer.id}/update/",
                           data={'content': content})
    assert response.status_code == 200
    assert message in response.data


def test_update_answer_for_logged_user_that_does_not_own_answer(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        test_user_2 = User(username='random_user',
                           email='random@gmail.com',
                           password=generate_password_hash('34somepassword34'))
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        answer = Answer(user=test_user,
                        question=question, content="My answer to your question.")
        db.session.add(answer)
        db.session.add(test_user_2)
        db.session.commit()
        db.session.refresh(answer)
        db.session.refresh(test_user)

    auth.login(email='random@gmail.com',
               password='34somepassword34')
    response = client.get(f'/answers/{answer.id}/update/')
    assert response.status_code == 403


def test_update_answer_for_not_logged_user(client):
    response = client.get('/answers/5678/update/')
    assert response.status_code == 302
    assert (response.headers["Location"].startswith('/auth/login/'))


def test_update_nonexistent_answer_by_logged_user(client, auth: AuthActions):
    auth.login()
    response = client.get("/answers/67890/update/")
    assert response.status_code == 404


def test_delete_question_for_logged_user_that_owns_answer(client, auth: AuthActions, app):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        answer = Answer(user=test_user,
                        question=question, content="My answer to your question.")
        db.session.add(answer)
        db.session.commit()
        db.session.refresh(answer)
        db.session.refresh(test_user)

    auth.login()
    question_id = answer.question_id
    response = client.post(f"/answers/{answer.id}/delete/")
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers["Location"] == f"/questions/{answer.question_id}/"
    assert messages["success"] == 'You successfully deleted your answer.'
    with app.app_context():
        answer = db.session.query(Answer).filter(
            (Answer.question_id == question_id) &
            (Answer.user_id == test_user.id)
        ).first()
        assert answer is None


def test_delete_answer_by_logged_user_that_does_not_own_answer(client, auth: AuthActions, app):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        test_user_2 = User(username='random_user',
                           email='random@gmail.com',
                           password=generate_password_hash('34somepassword34'))
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        answer = Answer(user=test_user,
                        question=question, content="My answer to your question.")
        db.session.add(answer)
        db.session.add(test_user_2)
        db.session.commit()
        db.session.refresh(answer)

    auth.login(email='random@gmail.com',
               password='34somepassword34')
    response = client.post(f'/answers/{answer.id}/delete/')
    assert response.status_code == 403


def test_delete_nonexistent_answer_by_logged_user(client, auth: AuthActions):
    auth.login()
    response = client.post("/answers/45678/delete/")
    assert response.status_code == 404


def test_delete_answer_by_not_logged_user(client):
    response = client.post("/answers/56789/delete/")
    assert response.status_code == 302
    assert (response.headers["Location"].startswith('/auth/login/'))


def test_upvote_answer_for_logged_user_without_vote(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        answer = Answer(user=test_user,
                        question=question, content="My answer to your question.")
        db.session.add(answer)
        db.session.commit()
        db.session.refresh(answer)
        db.session.refresh(test_user)

    auth.login()
    response = client.post(f'/answers/{answer.id}/upvote/')
    assert response.status_code == 302
    assert response.headers["Location"] == f'/questions/{answer.question_id}/'

    with app.app_context():
        upvote = db.session.query(AnswerVote).filter(
            (AnswerVote.answer_id == answer.id) &
            (AnswerVote.user_id == test_user.id) &
            (AnswerVote.is_upvote == True)
        ).first()
        assert upvote is not None


def test_upvote_answer_for_logged_user_with_upvote(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        answer = Answer(user=test_user,
                        question=question, content="My answer to your question.")
        upvote = AnswerVote(user=test_user,
                            answer=answer, is_upvote=True)
        db.session.add(upvote)
        db.session.commit()
        db.session.refresh(answer)
        db.session.refresh(test_user)

    auth.login()
    response = client.post(f'/answers/{answer.id}/upvote/')
    assert response.status_code == 302
    assert response.headers["Location"] == f'/questions/{answer.question_id}/'

    with app.app_context():
        upvote = db.session.query(AnswerVote).filter(
            (AnswerVote.answer_id == answer.id) &
            (AnswerVote.user_id == test_user.id) &
            (AnswerVote.is_upvote == True)
        ).first()
        assert upvote is None


def test_upvote_answer_for_logged_user_with_downvote(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        answer = Answer(user=test_user,
                        question=question, content="My answer to your question.")
        downvote = AnswerVote(user=test_user,
                              answer=answer, is_upvote=False)
        db.session.add(downvote)
        db.session.commit()
        db.session.refresh(answer)
        db.session.refresh(test_user)

    auth.login()
    response = client.post(f'/answers/{answer.id}/upvote/')
    assert response.status_code == 302
    assert response.headers["Location"] == f'/questions/{answer.question_id}/'

    with app.app_context():
        upvote = db.session.query(AnswerVote).filter(
            (AnswerVote.answer_id == answer.id) &
            (AnswerVote.user_id == test_user.id) &
            (AnswerVote.is_upvote == True)
        ).first()
        assert upvote is not None


def test_upvote_answer_for_not_logged_user(app, client):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        answer = Answer(user=test_user,
                        question=question, content="My answer to your question.")
        db.session.add(answer)
        db.session.commit()
        db.session.refresh(answer)

    response = client.post(f"/answers/{answer.id}/upvote/")
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers["Location"] == f'/questions/{answer.question_id}/'
    assert messages['info'] == 'To vote for an answer, become authenticated user.'


def test_upvote_nonexistent_answer(app, client):
    response = client.post("/answers/564/upvote/")
    assert response.status_code == 404


def test_downvote_answer_for_logged_user_without_vote(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        answer = Answer(user=test_user,
                        question=question, content="My answer to your question.")
        db.session.add(answer)
        db.session.commit()
        db.session.refresh(answer)
        db.session.refresh(test_user)

    auth.login()
    response = client.post(f'/answers/{answer.id}/downvote/')
    assert response.status_code == 302
    assert response.headers["Location"] == f'/questions/{answer.question_id}/'

    with app.app_context():
        downvote = db.session.query(AnswerVote).filter(
            (AnswerVote.answer_id == answer.id) &
            (AnswerVote.user_id == test_user.id) &
            (AnswerVote.is_upvote == False)
        ).first()
        assert downvote is not None


def test_downvote_answer_for_logged_user_with_downvote(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        answer = Answer(user=test_user,
                        question=question, content="My answer to your question.")
        downvote = AnswerVote(user=test_user,
                              answer=answer, is_upvote=False)
        db.session.add(downvote)
        db.session.commit()
        db.session.refresh(answer)
        db.session.refresh(test_user)

    auth.login()
    response = client.post(f'/answers/{answer.id}/downvote/')
    assert response.status_code == 302
    assert response.headers["Location"] == f'/questions/{answer.question_id}/'

    with app.app_context():
        downvote = db.session.query(AnswerVote).filter(
            (AnswerVote.answer_id == answer.id) &
            (AnswerVote.user_id == test_user.id) &
            (AnswerVote.is_upvote == False)
        ).first()
        assert downvote is None


def test_downvote_answer_for_logged_user_with_downvote(client, app, auth: AuthActions):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        answer = Answer(user=test_user,
                        question=question, content="My answer to your question.")
        upvote = AnswerVote(user=test_user,
                            answer=answer, is_upvote=True)
        db.session.add(upvote)
        db.session.commit()
        db.session.refresh(answer)
        db.session.refresh(test_user)

    auth.login()
    response = client.post(f'/answers/{answer.id}/downvote/')
    assert response.status_code == 302
    assert response.headers["Location"] == f'/questions/{answer.question_id}/'

    with app.app_context():
        downvote = db.session.query(AnswerVote).filter(
            (AnswerVote.answer_id == answer.id) &
            (AnswerVote.user_id == test_user.id) &
            (AnswerVote.is_upvote == False)
        ).first()
        assert downvote is not None


def test_downvote_answer_for_not_logged_user(app, client):
    with app.app_context():
        test_user = db.session.query(User).\
            filter_by(username='test_user').first()
        question = Question(user=test_user,
                            title='How to iterate through Python List?')
        answer = Answer(user=test_user,
                        question=question, content="My answer to your question.")
        db.session.add(answer)
        db.session.commit()
        db.session.refresh(answer)

    response = client.post(f"/answers/{answer.id}/downvote/")
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers["Location"] == f'/questions/{answer.question_id}/'
    assert messages['info'] == 'To vote for an answer, become authenticated user.'


def test_downvote_nonexistent_answer(app, client):
    response = client.post("/answers/564/upvote/")
    assert response.status_code == 404


def test_personal_page_for_logged_user(auth: AuthActions, client):
    auth.login()
    response = client.get("/personal/page/")
    assert response.status_code == 200
    assert b'Number of questions you asked' in response.data
    assert b'Number of questions you answered' in response.data


def test_personal_page_for_not_logged_user(client):
    response = client.get("/personal/page/")
    assert response.status_code == 302
    assert (response.headers["Location"].startswith("/auth/login/"))


def test_public_page(client):
    response = client.get("/users/test_user/")
    assert response.status_code == 200
    assert b'Number of questions test_user asked' in response.data
    assert b'Number of questions test_user answered' in response.data


def test_public_page_for_nonexistent_user(client):
    response = client.get("/users/fghjkliugyhjkihug/")
    assert response.status_code == 404


def test_personal_post_question(client, auth: AuthActions):
    auth.login()
    assert client.get('/personal/questions/ask/').status_code == 200
    response: Response = client.post('/personal/questions/ask/',
                                     data={'title': 'How to iterate through Python List?',
                                           'details': 'I am only starting to learn Python,\
                                do not know how to iterate through list',
                                           'tags': 'python, iteration, programming'})
    with client.session_transaction() as session:
        messages = dict(session['_flashes'])
    assert response.status_code == 302
    assert response.headers['Location'] == '/personal/page/'
    assert messages['success'] == 'You successfully asked new question!'


@pytest.mark.parametrize(('title', 'message'),
                         (
    ('', b'Title is required to post a question.'),
    ('dfrg',  b'Title is too short.')
))
def test_personal_post_question_validate_input(client, auth: AuthActions, title, message):
    auth.login()
    response: Response = client.post('/personal/questions/ask/',
                                     data={'title': title,
                                           'details': '',
                                           'tags': ''})
    assert response.status_code == 200
    assert message in response.data


def test_personal_post_question_for_not_logged_user(client):
    response = client.get('/personal/questions/ask/')
    assert response.status_code == 302
    assert (response.headers["Location"].startswith("/auth/login/"))


def test_search_with_empty_query(client):
    response = client.get("/questions/search/?query=")
    assert response.status_code == 200


def test_search_with_empty_query_that_starts_with_hashtag_sign(client):
    response = client.get("/questions/search/?query=#")
    assert response.status_code == 200


def test_search_for_question(client):
    query = "How"
    response = client.get(f"/questions/search/?query={query}")
    print(response.data)
    assert response.status_code == 200
    assert f"Number of questions found with <mark>{query}</mark>".encode(
        "utf-8") in response.data


def test_search_for_tag(client):
    tag = 'tag'
    response = client.get(
        f"/questions/search/?query=%{tag}", follow_redirects=True)
    assert response.status_code == 200
    print(response.data)
    assert b'Number of questions found with tag' in response.data
