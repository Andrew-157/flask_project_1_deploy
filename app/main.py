from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from .models import User, Question, Tag, QuestionViews, Answer, QuestionVote, AnswerVote, tagged_items
from . import db

bp = Blueprint('main', __name__)


def split_tags_string(tags_str: str) -> list[str]:
    # Takes a string of tags as an argument
    # and returns list of edited tags
    # For example:
    # 'python 3.x, javascript, ruby on rails ' will be
    # turned in ['python-3.x', 'javascript', 'ruby-on-rails']
    # and returned
    tags_to_return = []
    tags_list = tags_str.split(',')
    for tag in tags_list:
        if tag.isspace():
            pass
        elif not tag:
            pass
        else:
            tags_to_return.append(tag.strip())

    for index, tag in enumerate(tags_to_return):
        tags_to_return[index] = '-'.join(tag.split(' '))

    return tags_to_return


def upvote_downvote_question(question_id: int, user_id: int, is_upvote: bool):
    # pass to this function only existing questions
    # and authenticated users
    existing_vote = db.session.query(QuestionVote).\
        filter((QuestionVote.user_id == user_id) &
               (QuestionVote.question_id == question_id)).first()
    if not existing_vote:
        vote = QuestionVote(user_id=user_id,
                            question_id=question_id,
                            is_upvote=is_upvote)
        db.session.add(vote)
        db.session.commit()
        return None

    if existing_vote:
        if existing_vote.is_upvote == True:
            if is_upvote == True:
                db.session.delete(existing_vote)
                db.session.commit()
                return None
            elif is_upvote == False:
                existing_vote.is_upvote = False
                db.session.commit()
                return None
        elif existing_vote.is_upvote == False:
            if is_upvote == False:
                db.session.delete(existing_vote)
                db.session.commit()
                return None
            elif is_upvote == True:
                existing_vote.is_upvote = True
                db.session.commit()
                return None


def upvote_downvote_answer(answer_id: int, user_id: int, is_upvote: bool):
    existing_vote = db.session.query(AnswerVote).\
        filter((AnswerVote.answer_id == answer_id) &
               (AnswerVote.user_id == user_id)).first()

    if not existing_vote:
        vote = AnswerVote(
            answer_id=answer_id,
            user_id=user_id,
            is_upvote=is_upvote
        )
        db.session.add(vote)
        db.session.commit()
        return None

    if existing_vote:
        if existing_vote.is_upvote == True:
            if is_upvote == True:
                db.session.delete(existing_vote)
                db.session.commit()
                return None
            if is_upvote == False:
                existing_vote.is_upvote = False
                db.session.commit()
                return None
        if existing_vote.is_upvote == False:
            if is_upvote == False:
                db.session.delete(existing_vote)
                db.session.commit()
                return None
            if is_upvote == True:
                existing_vote.is_upvote = True
                db.session.commit()
                return None


@bp.route('/')
def index():
    tags = []
    for tag in db.session.query(Tag).\
            options(db.joinedload(Tag.questions)).all():
        if len(tag.questions) >= 1:
            tags.append(tag)
    return render_template('main/index.html', tags=tags)


@bp.route('/questions/ask/', methods=['GET', 'POST'])
def post_question():
    if not current_user.is_authenticated:
        flash('You need to be authenticated to ask a question.', 'info')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        title = request.form['title']
        details = request.form['details']
        tags = request.form['tags']
        errors = False

        if not title:
            flash('Title is required to post a question.')
            errors = True

        if title and len(title) > 300:
            flash('Title is too long.')
            errors = True

        if title and len(title) < 15:
            flash('Title is too short.')
            errors = True

        if errors:
            return render_template('main/post_question.html',
                                   title=title, details=details, tags=tags)

        question = Question(title=title,
                            details=details if details else None,
                            user_id=current_user.id)
        db.session.add(question)

        if tags.strip():
            tags = split_tags_string(tags)
            for tag in tags:
                existing_tag = db.session.execute(
                    db.select(Tag).filter_by(name=tag)).scalar_one_or_none()
                if existing_tag:
                    question.tags.append(existing_tag)
                else:
                    new_tag = Tag(name=tag)
                    question.tags.append(new_tag)
                    db.session.add(new_tag)

        db.session.commit()

        flash('You successfully asked new question!', 'success')
        return redirect(url_for('main.index'))

    return render_template('main/post_question.html')


@bp.route('/questions/<int:id>/update/', methods=['GET', 'POST'])
@login_required
def update_question(id):
    question = db.session.query(Question).\
        options(db.joinedload(Question.tags)).\
        filter_by(id=id).first()

    if not question:
        abort(404)

    if question.user != current_user:
        abort(403)

    if request.method == 'GET':

        if question.tags:
            tags_list = list(question.tags)
            for index, tag in enumerate(tags_list):
                tags_list[index] = tag.name
            tags = ','.join(tags_list)
        else:
            tags = None

        return render_template('main/update_question.html',
                               question=question,
                               tags=tags)

    if request.method == 'POST':

        title = request.form['title']
        details = request.form['details']
        tags = request.form['tags']
        errors = False

        if not title:
            flash('Title is required.')
            errors = True

        if title and len(title) > 300:
            flash('Title is too long.')
            errors = True

        if title and len(title) < 10:
            flash('Title is too short.')
            errors = True

        if errors:
            return render_template('main/update_question.html',
                                   question=question, tags=tags)

        question.title = title
        question.details = details
        question.updated = datetime.utcnow()

        if tags.strip():
            tags = split_tags_string(tags)
            tag_objects = []
            for tag in tags:
                existing_tag = db.session.query(Tag).\
                    filter_by(name=tag).first()
                if existing_tag:
                    tag_objects.append(existing_tag)
                else:
                    new_tag = Tag(name=tag)
                    tag_objects.append(new_tag)
                    db.session.add(new_tag)

            question.tags.clear()
            for tag_object in tag_objects:
                question.tags.append(tag_object)
        else:
            question.tags.clear()

        # if tags:
        #     tags = split_tags_string(tags)
        #     for question_tag in question.tags:
        #         if question_tag.name not in tags:
        #             question.tags.remove(question_tag)
        #         else:
        #             continue

        #     for tag in tags:
        #         existing_tag = db.session.query(
        #             Tag).filter_by(name=tag).first()
        #         if existing_tag:
        #             if existing_tag not in question.tags:
        #                 question.tags.append(existing_tag)
        #         else:
        #             new_tag = Tag(name=tag)
        #             question.tags.append(new_tag)
        #             db.session.add(new_tag)

        db.session.commit()
        flash('You successfully updated your question.', 'success')
        return redirect(url_for('main.question_detail', id=question.id))


@bp.route('/questions/<int:id>/', methods=['GET'])
def question_detail(id):

    question = db.session.query(Question).\
        options(db.joinedload(Question.times_viewed), db.joinedload(Question.user),
                db.joinedload(Question.tags)).\
        filter_by(id=id).first()

    if not question:
        abort(404)

    upvotes = db.session.query(QuestionVote).filter(
        (QuestionVote.question_id == question.id) &
        (QuestionVote.is_upvote == True)
    ).count()
    downvotes = db.session.query(QuestionVote).\
        filter(
        (QuestionVote.question_id == question.id) &
        (QuestionVote.is_upvote == False)
    ).count()

    if current_user.is_authenticated:
        question_views_obj = QuestionViews.query.filter(
            (QuestionViews.user_id == current_user.id)
            & (QuestionViews.question_id == question.id)
        ).first()
        if not question_views_obj:
            question_views_obj = QuestionViews(
                user_id=current_user.id,
                question_id=question.id
            )
            db.session.add(question_views_obj)
            db.session.commit()

        voting_status = db.session.query(QuestionVote).filter(
            (QuestionVote.question_id == question.id) &
            (QuestionVote.user_id == current_user.id)
        ).first()

    else:
        voting_status = None

    answers = db.session.query(Answer).options(
        db.joinedload(Answer.user)
    ).filter_by(question_id=question.id).all()

    answers_upvotes = {}
    answers_downvotes = {}
    for answer in answers:
        answers_upvotes[answer.id] = db.session.query(AnswerVote).filter(
            (AnswerVote.answer_id == answer.id) &
            (AnswerVote.is_upvote == True)
        ).count()
        answers_downvotes[answer.id] = db.session.query(AnswerVote).filter(
            (AnswerVote.answer_id == answer.id) &
            (AnswerVote.is_upvote == False)
        ).count()

    if current_user.is_authenticated:
        answer_votes_user = {}
        for answer in answers:
            user_vote = db.session.query(AnswerVote).filter(
                (AnswerVote.answer_id == answer.id) &
                (AnswerVote.user_id == current_user.id)
            ).first()
            if user_vote:
                answer_votes_user[answer.id] = user_vote
    else:
        answer_votes_user = {}

    return render_template('main/question_detail.html', question=question,
                           voting_status=voting_status, upvotes=upvotes,
                           downvotes=downvotes,
                           answers=answers,
                           answers_upvotes=answers_upvotes,
                           answers_downvotes=answers_downvotes,
                           answer_votes_user=answer_votes_user)


@bp.route('/questions/<int:id>/delete/', methods=['POST'])
@login_required
def delete_question(id):
    if request.method == 'POST':
        question = db.session.query(Question).\
            filter_by(id=id).first()

        if not question:
            abort(404)

        if question.user_id != current_user.id:
            abort(403)

        db.session.delete(question)
        db.session.commit()

        flash('You successfully deleted your question.', 'success')
        return redirect(url_for('main.index'))


@bp.route('/questions/<int:id>/upvote/', methods=['POST'])
def upvote_question(id):
    if request.method == 'POST':
        question = db.session.query(Question).filter_by(id=id).first()

        if not question:
            abort(404)

        if not current_user.is_authenticated:
            flash('You have to authenticate to vote for a question', 'info')
        else:
            upvote_downvote_question(question_id=question.id,
                                     user_id=current_user.id, is_upvote=True)

        return redirect(url_for('main.question_detail', id=question.id))


@bp.route('/questions/<int:id>/downvote/', methods=['POST'])
def downvote_question(id):
    if request.method == 'POST':
        question = db.session.query(Question).filter_by(id=id).first()

        if not question:
            abort(404)

        if not current_user.is_authenticated:
            flash('You have to authenticate to vote for a question', 'info')
        else:
            upvote_downvote_question(question_id=question.id,
                                     user_id=current_user.id, is_upvote=False)

        return redirect(url_for('main.question_detail', id=question.id))


@bp.route('/tags/<tag>/', methods=['GET'])
def questions_by_tag(tag):
    tag_object = db.session.query(Tag).\
        filter_by(name=tag).first()

    if not tag_object:
        return render_template('main/questions_by_tag.html', tag=tag, questions=[])

    questions = db.session.query(Question).\
        options(db.joinedload(Question.tags),
                db.joinedload(Question.user),
                db.joinedload(Question.times_viewed)).\
        filter(Question.tags.contains(tag_object)).\
        order_by(Question.asked.desc()).\
        all()

    answers_count = {}
    votes_count = {}
    for question in questions:
        answers_count[question.id] = db.session.query(Answer). \
            filter_by(question_id=question.id).count()
        votes_count[question.id] = db.session.query(QuestionVote).\
            filter_by(question_id=question.id).count()

    return render_template('main/questions_by_tag.html', tag=tag,
                           questions=questions,
                           answers_count=answers_count,
                           votes_count=votes_count)


@bp.route('/questions/<int:question_id>/answer/', methods=['POST', 'GET'])
def post_answer(question_id):
    question = db.session.query(Question).\
        filter_by(id=question_id).first()

    if not question:
        abort(404)

    if not current_user.is_authenticated:
        flash(
            'To leave an answer for a question, become an authenticated user.', 'info')
        return redirect(url_for('main.question_detail', id=question.id))

    if request.method == 'POST':
        content = request.form['content']
        errors = False

        if not content:
            flash('To publish an answer, you need to provide content for it.')
            errors = True

        if content and len(content) < 15:
            flash('Content of your answer is too short.')
            errors = True

        if errors:
            return render_template('main/post_answer.html',
                                   content=content,
                                   question=question)

        answer = Answer(content=content,
                        user_id=current_user.id,
                        question_id=question.id)

        db.session.add(answer)
        db.session.commit()

        flash('You successfully published your answer.', 'success')

        return redirect(url_for('main.question_detail', id=question.id))

    if request.method == 'GET':
        return render_template('main/post_answer.html',
                               question=question)


@bp.route('/answers/<int:id>/update/', methods=['POST', 'GET'])
@login_required
def update_answer(id):
    answer = db.session.query(Answer).\
        options(db.joinedload(Answer.question)).\
        filter_by(id=id).first()

    if not answer:
        abort(404)

    if answer.user_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        content = request.form['content']
        errors = False

        if not content:
            flash('You cannot update your answer without content.')
            errors = True

        if content and len(content) < 15:
            flash('Content of your answer is too short.')
            errors = True

        if errors:
            return render_template('main/update_answer.html',
                                   content=content,
                                   answer=answer,
                                   question=answer.question)

        answer.content = content
        answer.updated = datetime.utcnow()

        db.session.commit()

        flash('You successfully updated your answer.', 'success')

        return redirect(url_for('main.question_detail', id=answer.question_id))

    if request.method == 'GET':
        return render_template('main/update_answer.html', content=answer.content,
                               answer=answer,
                               question=answer.question)


@bp.route('/answers/<int:id>/delete/', methods=['POST'])
@login_required
def delete_answer(id):
    if request.method == 'POST':
        answer = db.session.query(Answer).\
            filter_by(id=id).first()

        if not answer:
            abort(404)

        if current_user.id != answer.user_id:
            abort(403)

        question_id = answer.question_id

        db.session.delete(answer)
        db.session.commit()

        flash('You successfully deleted your answer.', 'success')

        return redirect(url_for('main.question_detail', id=question_id))


@bp.route('/answers/<int:id>/upvote/', methods=['POST'])
def upvote_answer(id):
    if request.method == 'POST':
        answer = db.session.query(Answer).\
            filter_by(id=id).first()

        if not answer:
            abort(404)

        if not current_user.is_authenticated:
            flash('To vote for an answer, become authenticated user.', 'info')
        else:
            upvote_downvote_answer(answer.id, current_user.id, is_upvote=True)

        return redirect(url_for('main.question_detail', id=answer.question_id))


@bp.route('/answers/<int:id>/downvote/', methods=['POST'])
def downvote_answer(id):
    if request.method == 'POST':
        answer = db.session.query(Answer).\
            filter_by(id=id).first()

        if not answer:
            abort(404)

        if not current_user.is_authenticated:
            flash('To vote for an answer, become authenticated user.', 'info')
        else:
            upvote_downvote_answer(answer.id, current_user.id, is_upvote=False)

        return redirect(url_for('main.question_detail', id=answer.question_id))


@bp.route('/personal/page/')
@login_required
def personal_page():
    questions_asked = db.session.query(Question).\
        filter_by(user_id=current_user.id).all()

    questions_answered = []

    answers = db.session.query(Answer).\
        options(db.joinedload(Answer.question)).\
        filter_by(user_id=current_user.id).all()

    for answer in answers:
        if answer.question in questions_answered:
            continue
        else:
            questions_answered.append(answer.question)

    return render_template('main/personal_page.html',
                           questions_asked=questions_asked,
                           questions_answered=questions_answered)


@bp.route('/users/<username>/', methods=['GET'])
def public_page(username):
    user = db.session.query(User).\
        filter_by(username=username).first()
    if not user:
        abort(404)

    questions_asked = db.session.query(Question).\
        filter_by(user_id=user.id).all()

    questions_answered = []

    answers = db.session.query(Answer).\
        options(db.joinedload(Answer.question)).\
        filter_by(user_id=user.id).all()

    for answer in answers:
        if answer.question in questions_answered:
            continue
        else:
            questions_answered.append(answer.question)

    return render_template('main/public_page.html',
                           user=user,
                           questions_asked=questions_asked,
                           questions_answered=questions_answered)


@bp.route('/personal/questions/ask/', methods=['GET', 'POST'])
@login_required
def personal_post_question():
    # This is basically the same view for posting questions
    # just that it redirects to user's personal page instead of
    # index page
    if request.method == 'POST':
        title = request.form['title']
        details = request.form['details']
        tags = request.form['tags']
        errors = False

        if not title:
            flash('Title is required to post a question.')
            errors = True

        if title and len(title) > 300:
            flash('Title is too long.')
            errors = True

        if title and len(title) < 15:
            flash('Title is too short.')
            errors = True

        if errors:
            return render_template('main/personal_post_question.html',
                                   title=title, details=details, tags=tags)

        question = Question(title=title,
                            details=details if details else None,
                            user_id=current_user.id)
        db.session.add(question)

        if tags:
            tags = split_tags_string(tags)
            for tag in tags:
                existing_tag = db.session.execute(
                    db.select(Tag).filter_by(name=tag)).scalar_one_or_none()
                if existing_tag:
                    question.tags.append(existing_tag)
                else:
                    new_tag = Tag(name=tag)
                    question.tags.append(new_tag)
                    db.session.add(new_tag)

        db.session.commit()

        flash('You successfully asked new question!', 'success')
        return redirect(url_for('main.personal_page'))

    return render_template('main/personal_post_question.html')


@bp.route('/questions/search/', methods=['GET'])
def search():
    query = request.args.to_dict()['query']

    if not query.strip():
        return render_template('main/empty_search.html')

    if query.strip() == '#':
        return render_template('main/empty_search.html')

    if query.strip() == '%':
        return render_template('main/empty_search.html')

    if query[0] == '#' or query[0] == '%':
        return redirect(url_for('main.questions_by_tag', tag=query[1:]))

    questions = db.session.query(Question).\
        options(db.joinedload(Question.user),
                db.joinedload(Question.tags),
                db.joinedload(Question.times_viewed)).\
        filter((Question.title.contains(query)) |
               (Question.details.contains(query))).\
        order_by(Question.asked.desc()).all()

    answers_count = {}
    votes_count = {}
    for question in questions:
        answers_count[question.id] = db.session.query(Answer). \
            filter_by(question_id=question.id).count()
        votes_count[question.id] = db.session.query(QuestionVote).\
            filter_by(question_id=question.id).count()

    return render_template('main/search_results.html',
                           questions=questions,
                           answers_count=answers_count,
                           votes_count=votes_count,
                           query=query)
