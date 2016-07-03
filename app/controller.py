import inspect, os, sys
import simplejson as json
import reddit.connection
import app.controllers.front_page_controller
import app.controllers.subreddit_controller
import app.controllers.comment_controller
import app.controllers.moderator_controller
from utils.common import PageType
import app.cs_logger
from app.models import Base, SubredditPage, Subreddit, Post, ModAction

### LOAD ENVIRONMENT VARIABLES
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))), "..")
ENV = os.environ['CS_ENV']

with open(os.path.join(BASE_DIR, "config") + "/{env}.json".format(env=ENV), "r") as config:
    DBCONFIG = json.loads(config.read())

### LOAD SQLALCHEMY SESSION
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
db_engine = create_engine("mysql://{user}:{password}@{host}/{database}".format(
    host = DBCONFIG['host'],
    user = DBCONFIG['user'],
    password = DBCONFIG['password'],
    database = DBCONFIG['database']))

Base.metadata.bind = db_engine
DBSession = sessionmaker(bind=db_engine)
db_session = DBSession()

## LOAD LOGGER
log = app.cs_logger.get_logger(ENV, BASE_DIR)

conn = reddit.connection.Connect()

def fetch_reddit_front(page_type=PageType.TOP):
    r = conn.connect(controller="FetchRedditFront")
    fp = app.controllers.front_page_controller.FrontPageController(db_session, r, log)
    fp.archive_reddit_front_page(page_type)

def fetch_subreddit_front(sub_name, page_type = PageType.TOP):
    r = conn.connect(controller="FetchSubredditFront")
    sp = app.controllers.subreddit_controller.SubredditPageController(sub_name, db_session, r, log)
    sp.archive_subreddit_page(pg_type = page_type)

def fetch_post_comments(post_id):
    r = conn.connect(controller="FetchComments")
    cc = app.controllers.comment_controller.CommentController(db_session, r, log)
    cc.archive_missing_post_comments(post_id)

def fetch_missing_subreddit_post_comments(subreddit_id):
    r = conn.connect(controller="FetchComments")
    cc = app.controllers.comment_controller.CommentController(db_session, r, log)
    cc.archive_all_missing_subreddit_post_comments(subreddit_id)

def fetch_mod_action_history(subreddit, after_id = None):
    r = conn.connect(controller="ModLog")
    mac = app.controllers.moderator_controller.ModeratorController(subreddit, db_session, r, log)
    subreddit_id = db_session.query(Subreddit).filter(Subreddit.name == subreddit).first().id

    first_action_count = db_session.query(ModAction).filter(ModAction.subreddit_id == subreddit_id).count()
    log.info("Fetching Moderation Action History for {subreddit}. {n} actions are currently in the archive.".format(
        subreddit = subreddit,
        n = first_action_count))
    after_id = mac.archive_mod_action_page(after_id)
    db_session.commit()
    num_actions_stored = db_session.query(ModAction).filter(ModAction.subreddit_id == subreddit_id).count() - first_action_count

    while(num_actions_stored > 0):
        pre_action_count = db_session.query(ModAction).filter(ModAction.subreddit_id == subreddit_id).count()
        after_id = mac.archive_mod_action_page(after_id)
        db_session.commit()
        num_actions_stored = db_session.query(ModAction).filter(ModAction.subreddit_id == subreddit_id).count() - pre_action_count
   
    log.info("Finished Fetching Moderation Action History for {subreddit}. {stored} actions were stored, with a total of {total}.".format(
        subreddit = subreddit,
        stored = pre_action_count - first_action_count,
        total = pre_action_count))
